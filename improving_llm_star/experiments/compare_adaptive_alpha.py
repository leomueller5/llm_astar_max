"""Paired offline comparison of constant/adaptive guidance and standard A*."""

import argparse
import contextlib
import copy
import csv
import hashlib
import heapq
import io
import json
import math
import os
from pathlib import Path
import random
import statistics
from time import perf_counter

import measure_waypoint_progress as replay


os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(replay.WORKSPACE / ".venv/matplotlib"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


def load_cases(cache=None):
    if cache is None:
        return [{
            "id": name, "query": query,
            "llm_response": "Generated Path: " + json.dumps(waypoints),
            "source": "repository_prompt_example" if name == "public_prompt_example" else "hand_authored_fixture",
        } for name, query, waypoints in replay.fixtures()]
    data = json.loads(Path(cache).read_text())
    cases = data["cases"]
    if not cases:
        raise ValueError("The cache must contain at least one case")
    ids = set()
    for case in cases:
        if (not isinstance(case.get("query"), dict)
                or not isinstance(case.get("llm_response"), str)):
            raise ValueError("Each case requires a structured query and a raw llm_response string")
        if not isinstance(case.get("id"), str) or case["id"] in ids:
            raise ValueError("Each case requires a unique string id")
        ids.add(case["id"])
        case.setdefault("source", "user_supplied_cached_response")
    return cases


def standard_astar(planner, query):
    """Admissible Euclidean A* oracle with the planner's actual edge geometry.

    This reference rejects stale entries and never stores infinite-cost nodes;
    its operation/storage counts therefore differ from the legacy counters.
    """
    planner._initialize_parameters(copy.deepcopy(query))
    start, goal = planner.s_start, planner.s_goal
    started = perf_counter()
    g, parents = {start: 0.0}, {start: start}
    queue = [(math.dist(start, goal), start, 0.0)]
    expanded = 0
    path = []
    while queue:
        _, node, old_g = heapq.heappop(queue)
        if old_g != g[node]:
            continue
        expanded += 1
        if node == goal:
            path = [goal]
            while path[-1] != start:
                path.append(parents[path[-1]])
            path.reverse()
            break
        for neighbor in planner.get_neighbor(node):
            if not (planner.range_x[0] < neighbor[0] < planner.range_x[1]
                    and planner.range_y[0] < neighbor[1] < planner.range_y[1]):
                continue
            edge = planner.cost(node, neighbor)
            candidate = old_g + edge
            if candidate < g.get(neighbor, math.inf):
                g[neighbor] = candidate
                parents[neighbor] = node
                heapq.heappush(queue, (candidate + math.dist(neighbor, goal), neighbor, candidate))
    valid = planner._is_valid_path(path)
    length = sum(math.dist(a, b) for a, b in zip(path, path[1:])) if valid else None
    return {
        "operation": expanded, "storage": len(g), "length": length,
        "path": path, "processed_waypoints": None, "alpha_history": [],
        "waypoint_progress": [],
        "metrics": {"expanded_nodes": expanded, "unique_expanded_nodes": expanded,
                    "path_cost": length, "path_valid": valid, "goal_reached": bool(path),
                    "search_time_seconds": perf_counter() - started,
                    "alpha_adjustments": 0, "open_queue_rebuilds": 0},
    }


def run_variant(Planner, case, mode, adaptive_options):
    options = {"alpha": 0.5 if mode == "constant" else 1.0,
               "track_progress": True, "adaptive_alpha": mode == "adaptive"}
    if mode == "adaptive":
        options.update(adaptive_options)
    planner = Planner(**options)
    if mode == "astar":
        return standard_astar(planner, case["query"])
    with contextlib.redirect_stdout(io.StringIO()):
        result = planner.searching(copy.deepcopy(case["query"]))
    assert planner.model.calls == 1, "Only the cached initial response may be requested"
    return {
        "operation": result["operation"], "storage": result["storage"],
        "length": result["length"] if math.isfinite(result["length"]) else None,
        "path": planner.path, "processed_waypoints": planner.target_list,
        "metrics": planner.search_metrics, "alpha_history": planner.alpha_history,
        "waypoint_progress": planner.waypoint_progress,
    }


def compare(cases, adaptive_options, repeats=3, warmups=1, seed=42):
    if repeats < 1 or warmups < 0:
        raise ValueError("repeats must be >= 1 and warmups >= 0")
    replay.BACKEND = "installed"
    records, audits = [], []
    rng = random.Random(seed)
    for case in cases:
        Planner = replay.load_planner(replay.IMPROVED_ROOT, response=case["llm_response"])
        expected_waypoints = None
        original_sample = None
        for repetition in range(-warmups, repeats):
            modes = ["original", "constant", "adaptive", "astar"]
            rng.shuffle(modes)
            for mode in modes:
                sample = run_variant(Planner, case, mode, adaptive_options)
                if mode != "astar":
                    if expected_waypoints is None:
                        expected_waypoints = sample["processed_waypoints"]
                    assert sample["processed_waypoints"] == expected_waypoints
                if mode == "original":
                    original_sample = sample
                if repetition >= 0:
                    records.append({"case_id": case["id"], "mode": mode,
                                    "repeat": repetition, **sample})
        # Audit the alpha=1 control against the untouched original search source.
        Frozen = replay.load_planner(replay.WORKSPACE / "llm-astar", response=case["llm_response"])
        frozen = Frozen()
        try:
            result = replay.search(frozen, case["query"])
        except KeyError:
            if original_sample["metrics"]["goal_reached"]:
                raise AssertionError("Original source failed but alpha=1 control reached goal")
            audits.append({"case_id": case["id"], "status": "original_no_path_reconstruction_error"})
        else:
            assert result["operation"] == original_sample["operation"]
            assert result["storage"] == original_sample["storage"]
            assert result["length"] == original_sample["length"]
            assert frozen.plot.path == original_sample["path"]
            audits.append({"case_id": case["id"], "status": "matches_frozen_original"})
    return records, audits


def write_results(output, cases, options, records, audits, repeats, warmups, seed):
    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    for case in cases:
        samples = [r for r in records if r["case_id"] == case["id"]]
        oracle = next(r["length"] for r in samples if r["mode"] == "astar")
        for mode in ["original", "constant", "adaptive", "astar"]:
            group = [r for r in samples if r["mode"] == mode]
            valid = [r for r in group if r["metrics"]["path_valid"]]
            length = statistics.median(r["length"] for r in valid) if valid else None
            summaries.append({
                "case_id": case["id"], "mode": mode,
                "operation": statistics.median(r["operation"] for r in group),
                "storage": statistics.median(r["storage"] for r in group),
                "length": length,
                "relative_path_length_percent": 100 * length / oracle if length is not None and oracle else None,
                "valid_path_ratio": len(valid) / len(group),
                "median_search_seconds": statistics.median(r["metrics"]["search_time_seconds"] for r in group),
                "alpha_adjustments": statistics.median(r["metrics"]["alpha_adjustments"] for r in group),
                "queue_rebuilds": statistics.median(r["metrics"]["open_queue_rebuilds"] for r in group),
            })
    payload = {
        "scope": "Paired offline replay; fixture waypoints are not GPT-4o mini outputs",
        "actual_api_calls": 0, "adaptive_options": options, "repeats": repeats,
        "warmups": warmups, "order_seed": seed,
        "timing": "Search, reconstruction and validation; excludes environment setup, cached response processing, imports and plotting",
        "expansion_definition": "LLM variants: legacy heap pops including duplicates and goal; reference A*: non-stale pops",
        "original_source_audit": audits, "cases": cases,
        "planner_sha256": hashlib.sha256((replay.IMPROVED_ROOT / replay.PLANNER_PATH).read_bytes()).hexdigest(),
        "summaries": summaries, "runs": records,
    }
    (output / "comparison.json").write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    with (output / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    with (output / "alpha_events.csv").open("w", newline="") as stream:
        fields = ["case_id", "mode", "repeat", "expansion", "target_index", "target",
                  "reason", "old_alpha", "alpha", "best_distance",
                  "expansions_without_progress", "improvements", "open_size"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in records:
            for event in record["alpha_history"]:
                writer.writerow({k: record[k] for k in ["case_id", "mode", "repeat"]} | event)
    lines = ["# Adaptive alpha: paired offline comparison", "",
             "Actual API calls: 0. Default cases use fixed fixtures, not new model responses.", "",
             "| Case | Mode | Operations | Length | Relative to A* (%) | Median search (ms) | Alpha changes | Rebuilds | Valid |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for s in summaries:
        length = f'{s["length"]:.3f}' if s["length"] is not None else "failed"
        relative = f'{s["relative_path_length_percent"]:.2f}' if s["relative_path_length_percent"] is not None else "n/a"
        lines.append(f'| {s["case_id"]} | {s["mode"]} | {s["operation"]} | {length} | {relative} | '
                     f'{1000*s["median_search_seconds"]:.2f} | {s["alpha_adjustments"]} | '
                     f'{s["queue_rebuilds"]} | {s["valid_path_ratio"]:.0%} |')
    lines.extend(["", "These small, public/hand-authored cases are smoke tests, not generalization evidence.",
                  "Runtime includes measurement and queue maintenance. Alpha changes can reduce expansions while increasing runtime.",
                  "The original source is audited against the alpha=1 control outside timing. All three LLM variants use identical raw responses and progress logging.",
                  "The reference A* uses admissible Euclidean distance and identical legal edges, but rejects stale entries. Its operation/storage definitions differ from legacy LLM counters.",
                  "Positive waypoint weighting remains generally inadmissible; no optimality or fixed cost bound is guaranteed.",
                  "See comparison.json for full configuration, source hash, paths, and per-target progress; alpha_events.csv relates updates to progress.", ""])
    (output / "report.md").write_text("\n".join(lines))
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--output-dir", type=Path, default=replay.IMPROVED_ROOT / "experiments/results/adaptive_alpha")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    for flag, default, kind in [
        ("stagnation-threshold", 30, int), ("alpha-update-interval", 10, int),
        ("alpha-decrease", 0.2, float), ("alpha-increase", 0.1, float),
        ("alpha-min", 0.2, float), ("alpha-max", 1.0, float),
        ("progress-epsilon", 1e-9, float),
    ]:
        parser.add_argument("--" + flag, type=kind, default=default)
    args = parser.parse_args()
    options = {name: getattr(args, name) for name in [
        "stagnation_threshold", "alpha_update_interval", "alpha_decrease",
        "alpha_increase", "alpha_min", "alpha_max", "progress_epsilon",
    ]}
    cases = load_cases(args.cache)
    records, audits = compare(cases, options, args.repeats, args.warmups, args.seed)
    summaries = write_results(args.output_dir, cases, options, records, audits,
                              args.repeats, args.warmups, args.seed)
    for s in summaries:
        print(f'{s["case_id"]:28} {s["mode"]:9} operations={s["operation"]:4} '
              f'length={s["length"]} changes={s["alpha_adjustments"]}')
    print(f"Results: {args.output_dir}")


if __name__ == "__main__":
    main()
