"""Reproducible, API-free smoke measurement of waypoint progress.

The installed backend uses normal package dependencies and real Shapely geometry.
The isolated backend loads the planner class from its AST for dependency-free
checks, using an exact closed-segment predicate on integer fixtures instead.
Both backends substitute fixed model answers and disable plotting in comparisons.
This is not a GPT-4o mini benchmark or a normal-package integration test.
"""

import argparse
import ast
import contextlib
import copy
import csv
import heapq
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import runpy
from types import SimpleNamespace


IMPROVED_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = IMPROVED_ROOT.parent
PLANNER_PATH = Path("llmastar/pather/llm_a_star/llm_a_star.py")
BACKEND = "isolated"


def closed_segments_intersect(first, second):
    """Closed line intersection, including endpoints and collinear overlap."""
    a, b = first
    c, d = second

    def orientation(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def on_segment(p, q, r):
        return (min(p[0], q[0]) <= r[0] <= max(p[0], q[0])
                and min(p[1], q[1]) <= r[1] <= max(p[1], q[1]))

    o1, o2 = orientation(a, b, c), orientation(a, b, d)
    o3, o4 = orientation(c, d, a), orientation(c, d, b)
    if ((o1 > 0 > o2 or o2 > 0 > o1)
            and (o3 > 0 > o4 or o4 > 0 > o3)):
        return True
    return any((o == 0 and on_segment(p, q, r)) for o, p, q, r in [
        (o1, a, b, c), (o2, a, b, d), (o3, c, d, a), (o4, c, d, b),
    ])


class OfflineModel:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def ask(self, **kwargs):
        self.calls += 1
        return self.response

    def chat(self, *args, **kwargs):
        raise AssertionError("This measurement must use structured queries.")


class OfflinePlot:
    def __init__(self, *args):
        self.path = []

    def animation(self, path, *args):
        self.path = list(path)


def load_planner(root, waypoints):
    """Load the repository class with either installed or isolated dependencies."""
    path = root / PLANNER_PATH
    response = "Generated Path: " + json.dumps(waypoints)
    if BACKEND == "installed":
        name = f"llmastar.pather.llm_a_star._measurement_{root.name.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.ChatGPT = lambda **kwargs: OfflineModel(response)
        module.plotting = SimpleNamespace(Plotting=OfflinePlot)
        return module.LLMAStar

    tree = ast.parse(path.read_text(), filename=str(path))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    env = runpy.run_path(str(root / "llmastar/env/search/env.py"))
    utils = runpy.run_path(str(root / "llmastar/utils/utils.py"))
    prompts = runpy.run_path(str(root / "llmastar/pather/llm_a_star/prompt.py"))
    namespace = {
        "math": math, "heapq": heapq, "json": json,
        "env": SimpleNamespace(Env=env["Env"]),
        "plotting": SimpleNamespace(Plotting=OfflinePlot),
        "ChatGPT": lambda **kwargs: OfflineModel(response),
        "list_parse": utils["list_parse"],
        "is_lines_collision": closed_segments_intersect,
        **prompts,
    }
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["LLMAStar"]


def fixtures():
    def query(start, goal, vertical=None):
        return {
            "start": start, "goal": goal, "range_x": [0, 31],
            "range_y": [0, 21], "horizontal_barriers": [],
            "vertical_barriers": vertical or [],
        }

    wall = query([5, 10], [25, 10], [[15, 0, 14]])
    examples = [
        ("open_direct", query([3, 3], [25, 15]), [[3, 3], [14, 9], [25, 15]]),
        ("open_detour", query([3, 3], [25, 3]), [[3, 3], [3, 17], [25, 3]]),
        ("wall_bypass", wall, [[5, 10], [14, 15], [16, 15], [25, 10]]),
        ("wall_wrong_direction", wall, [[5, 10], [14, 5], [25, 10]]),
        ("wall_unreachable_endpoint", wall, [[5, 10], [15, 14], [25, 10]]),
    ]
    dataset = json.loads((IMPROVED_ROOT / "dataset/environment_50_30.json").read_text())
    example = dataset[0]
    public_query = {k: copy.deepcopy(example[k]) for k in [
        "range_x", "range_y", "horizontal_barriers", "vertical_barriers",
    ]}
    public_query.update(start=example["start_goal"][0][0], goal=example["start_goal"][0][1])
    examples.append(("public_prompt_example", public_query,
                     [[5, 5], [26, 9], [25, 23], [20, 20]]))
    return examples


def search(planner, query):
    with contextlib.redirect_stdout(io.StringIO()):
        result = planner.searching(copy.deepcopy(query))
    assert planner.model.calls >= 1
    path = planner.plot.path
    assert path[0] == tuple(query["start"]) and path[-1] == tuple(query["goal"])
    for a, b in zip(path, path[1:]):
        dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
        assert max(dx, dy) == 1 and not planner.is_collision(a, b)
    return result


def check_counter_behavior():
    Planner = load_planner(IMPROVED_ROOT, [[3, 3], [25, 15]])
    planner = Planner(alpha=0.5, track_progress=True)
    planner.i, planner.s_target = 1, (5, 0)
    planner._start_waypoint_measurement()
    for node in [(0, 0), (1, 0), (1, 1), (1, 0), (2, 0)]:
        planner._record_waypoint_progress(node)
    summary = planner.waypoint_progress[0]
    assert summary["expansions"] == 5
    assert summary["initial_distance"] == 5
    assert summary["best_distance"] == 3
    assert summary["improvements"] == 2
    assert summary["expansions_without_progress"] == 0
    assert summary["max_expansions_without_progress"] == 2
    planner.target_list = [(0, 0), (5, 0), (9, 0)]
    planner._update_target()
    assert len(planner.waypoint_progress) == 2
    assert planner.waypoint_progress[-1]["expansions"] == 0
    planner._record_waypoint_progress((2, 0))
    assert planner.waypoint_progress[-1]["initial_distance"] == 7
    assert planner.waypoint_progress[-1]["expansions_without_progress"] == 0
    assert planner.alpha == 0.5
    for first, second, expected in [
        ([(0, 0), (2, 2)], [(0, 2), (2, 0)], True),
        ([(0, 0), (1, 0)], [(1, 0), (2, 0)], True),
        ([(0, 0), (3, 0)], [(1, 0), (2, 0)], True),
        ([(0, 0), (1, 0)], [(2, 0), (3, 0)], False),
        ([(0, 0), (1, 0)], [(0, 1), (1, 1)], False),
    ]:
        assert closed_segments_intersect(first, second) == expected


def measure():
    check_counter_behavior()
    records = []
    for name, query, waypoints in fixtures():
        Planner = load_planner(IMPROVED_ROOT, waypoints)
        Original = load_planner(WORKSPACE / "llm-astar", waypoints)
        original = Original()
        original_result = search(original, query)
        for alpha in [0, 0.5, 1]:
            plain = Planner(alpha=alpha)
            observed = Planner(alpha=alpha, track_progress=True)
            plain_result = search(plain, query)
            result = search(observed, query)
            assert result == plain_result
            assert observed.PARENT == plain.PARENT
            assert observed.CLOSED == plain.CLOSED
            assert observed.plot.path == plain.plot.path
            assert not plain.waypoint_progress
            assert observed.alpha == alpha
            assert sum(s["expansions"] for s in observed.waypoint_progress) == result["operation"]
            for summary in observed.waypoint_progress:
                if summary["expansions"]:
                    assert summary["best_distance"] <= summary["initial_distance"]
            if alpha == 1:
                assert result == original_result
                assert observed.CLOSED == original.CLOSED
                assert observed.plot.path == original.plot.path
            summaries = copy.deepcopy(observed.waypoint_progress)
            # Reusing an instance must not accumulate summaries between searches.
            assert search(observed, query) == result
            assert observed.waypoint_progress == summaries
            records.append({
                "case": name,
                "waypoint_source": "repository_prompt_example" if name == "public_prompt_example" else "hand_authored_fixture",
                "alpha": alpha,
                "input_query": query,
                "raw_waypoints": waypoints,
                "result": result,
                "waypoint_progress": summaries,
                "max_stagnation": max(s["max_expansions_without_progress"] for s in summaries),
                "path_valid": True,
                "tracking_preserves_search": True,
            })
    return records


def main():
    global BACKEND
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["isolated", "installed"], default="isolated")
    parser.add_argument("--output-dir", type=Path,
                        default=None)
    args = parser.parse_args()
    BACKEND = args.backend
    if args.output_dir is None:
        suffix = "waypoint_progress_installed" if BACKEND == "installed" else "waypoint_progress"
        args.output_dir = IMPROVED_ROOT / "experiments/results" / suffix
    records = measure()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "measurement.json").write_text(json.dumps({
        "scope": "Offline smoke measurement; not a GPT-4o mini benchmark",
        "actual_api_calls": 0,
        "backend": BACKEND,
        "geometry": "Shapely" if BACKEND == "installed" else "Integer closed-segment intersection substituted for Shapely",
        "expansion_definition": "Heap pops, including duplicate states and the goal pop",
        "baseline_definition": "First popped state for each newly activated target",
        "progress_tolerance": 1e-9,
        "planner_sha256": hashlib.sha256((IMPROVED_ROOT / PLANNER_PATH).read_bytes()).hexdigest(),
        "original_planner_sha256": hashlib.sha256((WORKSPACE / "llm-astar" / PLANNER_PATH).read_bytes()).hexdigest(),
        "records": records,
    }, indent=2) + "\n")
    with (args.output_dir / "summary.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case", "alpha", "operation", "storage", "length",
                         "target_activations", "max_stagnation", "path_valid"])
        for row in records:
            r = row["result"]
            writer.writerow([row["case"], row["alpha"], r["operation"], r["storage"],
                             r["length"], len(row["waypoint_progress"]),
                             row["max_stagnation"], row["path_valid"]])
            print(f'{row["case"]:28} alpha={row["alpha"]:<3} '
                  f'operations={r["operation"]:4} length={r["length"]:7.2f} '
                  f'max_stagnation={row["max_stagnation"]:4}')
    report = [
        "# Offline-Messung des Waypoint-Fortschritts", "",
        "Sechs feste Testfälle, jeweils mit alpha = 0, 0.5 und 1. "
        "Keine echten LLM-Aufrufe; keine adaptive Gewichtsänderung.", "",
        f"Backend: {BACKEND}. Kollisionsprüfung: " + ("echtes Shapely." if BACKEND == "installed" else "isolierter Segmenttest."), "",
        "| Fall | alpha | Operationen | Storage | Pfadlänge | Max. Stillstand |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in records:
        r = row["result"]
        report.append(f'| {row["case"]} | {row["alpha"]} | {r["operation"]} | '
                      f'{r["storage"]} | {r["length"]:.4f} | {row["max_stagnation"]} |')
    report.extend([
        "", "## Prüfungen", "",
        "- Alle 18 Vergleiche mit/ohne Messung haben identische Ergebnisse, Pfade, "
        "Vorgänger und Heap-Pop-Reihenfolgen.",
        "- alpha=1 stimmt in allen sechs Fällen mit dem Original überein.",
        "- Alle ausgegebenen Pfade wurden auf Endpunkte, legale Schritte und Kollisionen geprüft.",
        "- Zähler-Resets bei Fortschritt, Waypoint-Wechsel und erneutem Suchlauf wurden geprüft.",
        "", "## Einordnung", "",
        "Der Stillstandszähler erfasst aufeinanderfolgende Heap-Pops ohne eine neue "
        "beste euklidische Distanz zum aktiven Waypoint. Duplikate und der Ziel-Pop "
        "werden wie beim bisherigen operation-Zähler mitgezählt. Der erste Pop "
        "eines neuen Targets legt den Distanz-Ausgangswert fest.", "",
        "Ein hilfreicher Waypoint spart im offenen Direktfall Operationen; ein "
        "unnötiger Umweg-Waypoint erhöht sie im offenen Umwegfall. Ein sinnvoller "
        "Waypoint im öffentlichen Prompt-Beispiel hat bei alpha=1 ebenfalls "
        "26 Pops Stillstand vor dem nächsten Fortschritt. Der Umwegfall hat 25. "
        "Ein einzelner Grenzwert trennt diese Beispiele daher nicht zuverlässig.", "",
        "Im Endpoint-Fall schaltet die Original-Logik bereits beim Erzeugen des "
        "Nachbarn um, obwohl der Target-Punkt auf einem Hindernis liegt. Diese "
        "unveränderte Logik kann problematische Waypoints vor der Messung verbergen.", "",
        "Dies ist ein Offline-Funktionstest mit handgeschriebenen Waypoints "
        "und einem Beispiel aus dem Repository-Prompt, kein GPT-4o-mini-Benchmark. "
        "Im installed-Backend werden die echten Paketabhängigkeiten inklusive "
        "Shapely importiert. Im isolated-Backend werden optionale Imports umgangen "
        "und ein Segmenttest ersetzt Shapely. Keine Laufzeit-, Kosten- oder "
        "Generalisierungsverbesserung wird daraus abgeleitet.", "",
    ])
    (args.output_dir / "report.md").write_text("\n".join(report))
    print(f"PASS: {len(records)} paired runs preserve results, paths, and pop order.")
    print("PASS: alpha=1 matches the original on all six fixtures.")
    print("PASS: counters reset on progress, target changes, and repeated searches.")
    print(f"Results: {args.output_dir}")


if __name__ == "__main__":
    main()
