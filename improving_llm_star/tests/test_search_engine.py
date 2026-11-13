import copy
import heapq
import math

import pytest

from .test_offline_environment import measurement, ROOT


@pytest.fixture
def planner_class(monkeypatch):
    monkeypatch.setattr(measurement, "BACKEND", "installed")

    def make(waypoints=None):
        return measurement.load_planner(ROOT, waypoints or [[3, 3], [8, 3]])

    return make


def small_query():
    return {"start": [3, 3], "goal": [8, 3], "range_x": [0, 11],
            "range_y": [0, 9], "horizontal_barriers": [], "vertical_barriers": []}


@pytest.mark.parametrize("options,factor", [
    ({"alpha": 1}, 2), ({"alpha": 0.5}, 1.5),
    ({"adaptive_alpha": True}, 1),
])
def test_final_goal_formula_is_explicit(planner_class, options, factor):
    p = planner_class()(**options)
    p._initialize_parameters(small_query())
    p.s_target = p.s_goal
    assert p.heuristic(p.s_start) == factor * math.dist(p.s_start, p.s_goal)


def test_final_goal_never_adjusts_alpha_or_rebuilds_from_controller(planner_class):
    p = planner_class([[3, 3], [3, 5], [8, 3]])(
        adaptive_alpha=True, stagnation_threshold=1, alpha_update_interval=1)
    calls = []
    maybe = p._maybe_update_alpha

    def observe():
        before = (p.alpha, p.alpha_adjustments, p.open_queue_rebuilds)
        final = p.s_target == p.s_goal
        maybe()
        if final:
            assert (p.alpha, p.alpha_adjustments, p.open_queue_rebuilds) == before
            calls.append(before)

    p._maybe_update_alpha = observe
    measurement.search(p, small_query())
    assert calls
    final_index = next(i for i, e in enumerate(p.alpha_history) if e["reason"] == "final_goal")
    assert p.alpha_history[final_index + 1:] == []
    assert all(e["target"] != p.s_goal for e in p.alpha_history
               if e["reason"] in {"stagnation", "progress"})
    assert p.search_metrics["final_goal_weight"] == 0


def test_stale_and_closed_entries_do_not_increment_progress(planner_class):
    p = planner_class()(alpha=0, robust_search=True, track_progress=True)
    push = p._push_open

    def inject(s):
        push(s)
        if s == p.s_start:
            heapq.heappush(p.OPEN, (-100, s, 999))  # Old cost snapshot: reject.
            heapq.heappush(p.OPEN, (p.f_value(s), s, p.g[s]))  # Reject after first expansion.

    p._push_open = inject
    measurement.search(p, small_query())
    m = p.search_metrics
    assert m["stale_pops"] == 1 and m["closed_pops"] == 1
    assert m["duplicate_pops"] == 1
    assert m["heap_pops"] == m["expanded_nodes"] + 2
    assert m["expanded_nodes"] == m["unique_expanded_nodes"]
    assert sum(s["expansions"] for s in p.waypoint_progress) == m["expanded_nodes"]


def test_rebuild_preserves_live_reopens_and_prunes_obsolete_versions(planner_class):
    p = planner_class()(adaptive_alpha=True)
    p._initialize_parameters(small_query())
    p.i, p.s_target = 1, (5, 5)
    a, b, c = (4, 3), (4, 4), (3, 4)
    p.g = {a: 5, b: 2, c: 3}
    p._closed_g = {a: 7, b: 2}
    p.OPEN = [(100, a, 8), (100, a, 5), (100, a, 5),
              (100, b, 2), (100, c, 3)]
    p._set_alpha(0.6, "stagnation")
    p._update_queue()
    assert {node for _, node, _ in p.OPEN} == {a, c}
    assert len(p.OPEN) == 2 and p.pruned_open_entries == 3
    assert all(key == p.f_value(node) and saved_g == p.g[node]
               for key, node, saved_g in p.OPEN)
    assert p.OPEN[0] == min(p.OPEN)


def test_improved_path_reopens_a_closed_state_and_propagates_cost(planner_class):
    # A directed subset of legal grid edges, with actual Euclidean edge costs.
    # The intentionally inconsistent B heuristic makes A close via the detour.
    s, u, v, a, b, goal = (3, 3), (4, 3), (5, 3), (4, 4), (3, 4), (5, 4)
    graph = {s: [u, b], u: [v], v: [a], a: [goal], b: [a]}
    query = small_query()
    query["goal"] = list(goal)
    paths = []
    for robust in [False, True]:
        p = planner_class([list(s), list(goal)])(alpha=0, robust_search=robust, track_progress=True)
        p.get_neighbor = lambda node: graph.get(node, [])
        p.heuristic = lambda node: 2.6 if node == b else 0
        result = measurement.search(p, copy.deepcopy(query))
        assert p.search_metrics["path_valid"]
        assert p.g[goal] == pytest.approx(sum(math.dist(x, y) for x, y in zip(p.path, p.path[1:])))
        paths.append(result["length"])
        if robust:
            assert p.CLOSED.count(a) == 2
            assert p.search_metrics["reopened_expansions"] == 1
            assert p.search_metrics["duplicate_pops"] == 0  # A useful reopen is not a rejected duplicate.
            assert p.path == [s, b, a, goal]
    assert paths[0] == pytest.approx(3 + math.sqrt(2))
    assert paths[1] == 3
