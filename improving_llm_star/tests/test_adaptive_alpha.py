import copy
import heapq
import math

import pytest

from .test_offline_environment import measurement, ROOT


@pytest.fixture
def controller(monkeypatch):
    monkeypatch.setattr(measurement, "BACKEND", "installed")

    def make(**kwargs):
        # These tests exercise the controller with hand-built legacy heap pairs.
        # Production engine behavior is covered by test_search_engine.py.
        kwargs.setdefault("robust_search", False)
        Planner = measurement.load_planner(ROOT, [[3, 3], [10, 10], [25, 15]])
        planner = Planner(adaptive_alpha=True, **kwargs)
        planner._initialize_parameters({
            "start": [3, 3], "goal": [25, 15], "range_x": [0, 31],
            "range_y": [0, 21], "horizontal_barriers": [], "vertical_barriers": [],
        })
        planner.i = 1
        planner.target_list = [(3, 3), (10, 10), (20, 12), (25, 15)]
        planner.s_target = (10, 10)
        planner.alpha = planner.alpha_max
        planner._start_waypoint_measurement()
        planner.g = {(3, 3): 0, (4, 4): math.sqrt(2)}
        planner.OPEN = [(planner.f_value(s), s) for s in planner.g]
        heapq.heapify(planner.OPEN)
        return planner

    return make


def observe(planner, node):
    planner.CLOSED.append(node)
    planner._record_waypoint_progress(node)
    planner._maybe_update_alpha()


def test_stagnation_decrease_waits_for_interval_and_refreshes_open(controller):
    p = controller(stagnation_threshold=3, alpha_update_interval=2)
    for _ in range(3):
        observe(p, (5, 10))
    assert p.alpha == 1 and p.open_queue_rebuilds == 0
    observe(p, (5, 10))
    assert p.alpha == 0.8 and p.open_queue_rebuilds == 1
    assert all(key == p.f_value(node) for key, node in p.OPEN)
    assert p.alpha_history[-1]["expansions_without_progress"] == 3
    assert p.alpha_history[-1]["expansion"] == 4


def test_progress_resumes_and_weight_recovers(controller):
    p = controller(stagnation_threshold=3, alpha_update_interval=2)
    for _ in range(4):
        observe(p, (5, 10))
    observe(p, (6, 10))
    assert p.alpha == 0.8
    observe(p, (7, 10))
    assert p.alpha == 0.9
    assert p.alpha_history[-1]["reason"] == "progress"
    observe(p, (8, 10))
    observe(p, (9, 10))
    assert p.alpha == 1


def test_bounds_and_no_rebuild_when_clamped(controller):
    p = controller(stagnation_threshold=1, alpha_update_interval=2)
    for _ in range(20):
        observe(p, (5, 10))
    assert p.alpha == 0.2
    assert p.alpha_adjustments == p.open_queue_rebuilds == 4
    assert all(0.2 <= e["alpha"] <= 1 for e in p.alpha_history)
    count = p.open_queue_rebuilds
    for _ in range(10):
        observe(p, (5, 10))
    assert p.open_queue_rebuilds == count


def test_target_reset_uses_one_shared_queue_rebuild(controller):
    p = controller(stagnation_threshold=1, alpha_update_interval=2)
    observe(p, (5, 10))
    observe(p, (5, 10))
    assert p.alpha == 0.8
    before = p.open_queue_rebuilds
    p._update_target()
    assert p.alpha == 1
    assert p.waypoint_progress[-1]["alpha"] == 1
    assert p.waypoint_progress[-1]["expansions"] == 0
    assert p.open_queue_rebuilds == before
    p._update_queue()  # Same single refresh as the production neighbor loop.
    assert p.open_queue_rebuilds == before + 1
    assert all(key == p.f_value(node) for key, node in p.OPEN)


def test_recovery_requires_new_progress_in_current_interval(controller):
    p = controller(stagnation_threshold=50, alpha_update_interval=2)
    p.alpha = 0.5
    observe(p, (5, 10))
    observe(p, (6, 10))
    assert p.alpha == 0.6
    observe(p, (6, 10))
    observe(p, (6, 10))
    assert p.alpha == 0.6


def test_meaningful_progress_tolerance(controller):
    p = controller(progress_epsilon=0.5, alpha_update_interval=10)
    observe(p, (5, 10))
    observe(p, (5.2, 10))
    assert p.waypoint_progress[-1]["improvements"] == 0
    observe(p, (5.6, 10))
    assert p.waypoint_progress[-1]["improvements"] == 1


def test_empty_queue_needs_no_refresh(controller):
    p = controller(stagnation_threshold=1, alpha_update_interval=2)
    p.OPEN = []
    observe(p, (5, 10))
    observe(p, (5, 10))
    assert p.alpha == 0.8 and p.open_queue_rebuilds == 0


def test_open_selection_changes_when_guidance_is_weakened(controller):
    p = controller(stagnation_threshold=1, alpha_update_interval=2)
    p.s_goal, p.s_target = (25, 3), (3, 17)
    p.g = {(3, 16): 13, (25, 3): 22}
    p.OPEN = [(p.f_value(node), node) for node in p.g]
    heapq.heapify(p.OPEN)
    assert p.OPEN[0][1] == (3, 16)
    for _ in range(4):
        observe(p, (3, 3))
    assert p.alpha == 0.6
    assert p.OPEN[0][1] == (25, 3)
    assert all(key == p.f_value(node) for key, node in p.OPEN)


def test_no_rebuild_for_progress_at_upper_bound(controller):
    p = controller(alpha_update_interval=2)
    for x in [3, 4, 5, 6]:
        observe(p, (x, 10))
    assert p.alpha == 1
    assert p.alpha_adjustments == p.open_queue_rebuilds == 0


def test_custom_bounds_are_respected(controller):
    p = controller(alpha_min=0.4, alpha_max=0.8, stagnation_threshold=1,
                   alpha_update_interval=2, alpha_decrease=0.3)
    for _ in range(8):
        observe(p, (5, 10))
    assert p.alpha == 0.4
    p._update_target()
    assert p.alpha == 0.8


def test_positive_waypoint_term_is_not_admissible(controller):
    p = controller()
    # In an open map the true remaining cost at the goal is zero.
    assert p.heuristic(p.s_goal) > 0


def test_adaptive_search_resets_each_run_and_does_not_call_model_again(monkeypatch):
    monkeypatch.setattr(measurement, "BACKEND", "installed")
    _, query, waypoints = measurement.fixtures()[1]
    Planner = measurement.load_planner(ROOT, waypoints)
    p = Planner(alpha=0.3, adaptive_alpha=True, stagnation_threshold=3,
                alpha_update_interval=2)
    first = measurement.search(p, query)
    events = copy.deepcopy(p.alpha_history)
    assert events[0]["alpha"] == 1
    assert p.alpha_adjustments > 0
    assert p.model.calls == 1
    assert all(0.2 <= e["alpha"] <= 1 for e in events)
    assert measurement.search(p, query) == first
    assert p.alpha_history == events
    assert p.model.calls == 2  # Exactly one initial response per search.


def test_no_path_reports_failure_instead_of_reconstructing_missing_goal(monkeypatch):
    monkeypatch.setattr(measurement, "BACKEND", "installed")
    Planner = measurement.load_planner(ROOT, [[3, 3], [8, 3]])
    p = Planner(adaptive_alpha=True)
    query = {"start": [3, 3], "goal": [8, 3], "range_x": [0, 11],
             "range_y": [0, 9], "horizontal_barriers": [],
             "vertical_barriers": [[5, 0, 8]]}
    result = p.searching(copy.deepcopy(query))
    assert result["length"] == math.inf and p.path == []
    assert p.search_metrics["path_valid"] is False
    assert p.search_metrics["path_cost"] is None
    assert p.search_metrics["goal_reached"] is False


@pytest.mark.parametrize("options", [
    {"alpha_min": 1.1}, {"alpha_max": 1.1}, {"alpha_min": -0.1},
    {"alpha_decrease": 0}, {"alpha_increase": -1},
    {"stagnation_threshold": 0}, {"alpha_update_interval": 0},
    {"alpha_update_interval": True}, {"progress_epsilon": -1},
    {"alpha_max": float("nan")},
])
def test_invalid_configuration_fails_early(controller, options):
    with pytest.raises(ValueError):
        controller(**options)
