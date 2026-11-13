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

MAIN_MODES = ["original", "constant", "adaptive", "astar"]
# Explicit ablations keep engine, final scoring, and adaptation effects distinct.
CONTROL_OPTIONS = {
    "adaptive_before": {"adaptive_alpha": True, "robust_search": False, "intermediate_only": False},
    "adaptive_engine_only": {"adaptive_alpha": True, "robust_search": True, "intermediate_only": False},
    "adaptive_goal_only": {"adaptive_alpha": True, "robust_search": False},
    "original_fixed_engine": {"alpha": 1.0, "robust_search": True},
    "constant_fixed_engine": {"alpha": 0.5, "robust_search": True},
    "constant_goal_only": {"alpha": 0.5, "robust_search": True, "final_goal_weight": 0.0},
    "fixed_waypoints_goal_only": {"alpha": 1.0, "robust_search": True, "final_goal_weight": 0.0},
}


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
    expanded = heap_pops = stale_pops = duplicate_pops = 0
    seen = set()
    path = []
    while queue:
        _, node, old_g = heapq.heappop(queue)
        heap_pops += 1
        if old_g != g[node]:
            stale_pops += 1
            duplicate_pops += int(node in seen)
            continue
        expanded += 1
        seen.add(node)
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
        "operation": heap_pops, "storage": len(g), "length": length,
        "path": path, "processed_waypoints": None, "alpha_history": [],
        "waypoint_progress": [],
        "metrics": {"expanded_nodes": expanded, "unique_expanded_nodes": expanded,
                    "heap_pops": heap_pops, "duplicate_pops": duplicate_pops,
                    "stale_pops": stale_pops, "closed_pops": 0,
                    "reopened_expansions": 0, "pruned_open_entries": 0,
                    "path_cost": length, "path_valid": valid, "goal_reached": bool(path),
                    "search_time_seconds": perf_counter() - started,
                    "alpha_adjustments": 0, "open_queue_rebuilds": 0},
    }


def run_variant(Planner, case, mode, adaptive_options):
    options = {"alpha": 0.5 if mode == "constant" else 1.0,
               "track_progress": True, "adaptive_alpha": mode == "adaptive"}
    if mode == "adaptive" or mode.startswith("adaptive_"):
        options.update(adaptive_options)
    options.update(CONTROL_OPTIONS.get(mode, {}))
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


def compare(cases, adaptive_options, repeats=3, warmups=1, seed=42, include_controls=False):
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
            modes = MAIN_MODES + (list(CONTROL_OPTIONS) if include_controls else [])
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
        modes = MAIN_MODES + [m for m in CONTROL_OPTIONS if any(r["mode"] == m for r in samples)]
        for mode in modes:
            group = [r for r in samples if r["mode"] == mode]
            valid = [r for r in group if r["metrics"]["path_valid"]]
            length = statistics.median(r["length"] for r in valid) if valid else None
            summaries.append({
                "case_id": case["id"], "mode": mode,
                "operation": statistics.median(r["operation"] for r in group),
                "expanded_nodes": statistics.median(r["metrics"]["expanded_nodes"] for r in group),
                "distinct_states": statistics.median(r["metrics"]["unique_expanded_nodes"] for r in group),
                "duplicate_pops": statistics.median(r["metrics"]["duplicate_pops"] for r in group),
                "stale_pops": statistics.median(r["metrics"]["stale_pops"] for r in group),
                "reopened_expansions": statistics.median(r["metrics"]["reopened_expansions"] for r in group),
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
        "operation_definition": "Raw heap pops including rejected stale/closed entries and goal",
        "expansion_definition": "Accepted processing only; reopens count again; skipped stale/closed entries do not update progress",
        "control_options": CONTROL_OPTIONS,
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
        fields += ["heap_pops", "effective_alpha"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in records:
            for event in record["alpha_history"]:
                writer.writerow({k: record[k] for k in ["case_id", "mode", "repeat"]} | event)
    lines = ["# Adaptive alpha: paired offline comparison", "",
             "Actual API calls: 0. Default cases use fixed fixtures, not new model responses.", "",
             "| Case | Mode | Heap pops | Expansions | Distinct | Duplicate pops | Reopens | Length | Relative to A* (%) | Median search (ms) | Alpha changes | Rebuilds | Valid |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for s in summaries:
        length = f'{s["length"]:.3f}' if s["length"] is not None else "failed"
        relative = f'{s["relative_path_length_percent"]:.2f}' if s["relative_path_length_percent"] is not None else "n/a"
        lines.append(f'| {s["case_id"]} | {s["mode"]} | {s["operation"]} | {s["expanded_nodes"]} | '
                     f'{s["distinct_states"]} | {s["duplicate_pops"]} | {s["reopened_expansions"]} | {length} | {relative} | '
                     f'{1000*s["median_search_seconds"]:.2f} | {s["alpha_adjustments"]} | '
                     f'{s["queue_rebuilds"]} | {s["valid_path_ratio"]:.0%} |')
    lines.extend(["", "These small, public/hand-authored cases are smoke tests, not generalization evidence.",
                  "Runtime includes measurement and queue maintenance. Alpha changes can reduce expansions while increasing runtime.",
                  "The original source is audited against the alpha=1 legacy-engine control outside timing. All LLM variants use identical raw responses and progress logging.",
                  "Original final score: g+2h; constant 0.5: g+1.5h; corrected adaptive: g+h at final goal. Controls isolate these scoring and engine differences.",
                  "Operations count every heap pop. Distinct states, accepted expansions, skipped stale entries, and legitimate reopens are reported separately. Standard A* does not store infinite-cost states, unlike legacy storage counting.",
                  "Positive waypoint weighting remains generally inadmissible; no optimality or fixed cost bound is guaranteed.",
                  "See comparison.json for full configuration, source hash, paths, and per-target progress; alpha_events.csv relates updates to progress.", ""])
    (output / "report.md").write_text("\n".join(lines))
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--output-dir", type=Path, default=replay.IMPROVED_ROOT / "experiments/results/adaptive_alpha_corrected")
    parser.add_argument("--include-controls", action="store_true")
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
    records, audits = compare(cases, options, args.repeats, args.warmups, args.seed, args.include_controls)
    summaries = write_results(args.output_dir, cases, options, records, audits,
                              args.repeats, args.warmups, args.seed)
    for s in summaries:
        print(f'{s["case_id"]:28} {s["mode"]:9} operations={s["operation"]:4} '
              f'length={s["length"]} changes={s["alpha_adjustments"]}')
    print(f"Results: {args.output_dir}")


if __name__ == "__main__":
    main()
