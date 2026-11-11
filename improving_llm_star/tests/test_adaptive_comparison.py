import importlib
import json
import math

import pytest

from .test_offline_environment import ROOT


@pytest.fixture
def comparison(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "experiments"))
    return importlib.import_module("compare_adaptive_alpha")


def test_paired_cached_comparison_and_logged_outputs(comparison, tmp_path):
    case = comparison.load_cases()[1]
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps({"cases": [case]}))
    cases = comparison.load_cases(cache)
    before = json.dumps(cases, sort_keys=True)
    records, audits = comparison.compare(
        cases, {"stagnation_threshold": 3, "alpha_update_interval": 2},
        repeats=1, warmups=0,
    )
    assert json.dumps(cases, sort_keys=True) == before
    assert len(records) == 4 and audits[0]["status"] == "matches_frozen_original"
    guided = [r for r in records if r["mode"] != "astar"]
    assert all(r["processed_waypoints"] == guided[0]["processed_waypoints"] for r in guided)
    oracle = next(r for r in records if r["mode"] == "astar")
    assert oracle["length"] == 22
    assert all(r["length"] >= oracle["length"] - 1e-9 for r in guided)
    assert all(r["metrics"]["path_valid"] for r in records)
    comparison.write_results(tmp_path / "out", cases, {}, records, audits, 1, 0, 42)
    output = json.loads((tmp_path / "out/comparison.json").read_text())
    assert output["actual_api_calls"] == 0
    assert (tmp_path / "out/alpha_events.csv").read_text().count("stagnation") > 0
    assert {r["mode"] for r in output["summaries"]} == {"original", "constant", "adaptive", "astar"}


def test_empty_cache_is_rejected(comparison, tmp_path):
    cache = tmp_path / "empty.json"
    cache.write_text('{"cases": []}')
    with pytest.raises(ValueError):
        comparison.load_cases(cache)


def test_reference_astar_uses_legal_detour_around_wall(comparison):
    case = comparison.load_cases()[2]
    comparison.replay.BACKEND = "installed"
    Planner = comparison.replay.load_planner(ROOT, response=case["llm_response"])
    sample = comparison.run_variant(Planner, case, "astar", {})
    assert sample["length"] == pytest.approx(10 + 10 * math.sqrt(2))
    assert sample["metrics"]["path_valid"]


def test_unsolvable_cases_remain_in_comparison(comparison, tmp_path):
    case = {
        "id": "disconnected", "source": "test_fixture",
        "query": {"start": [3, 3], "goal": [8, 3], "range_x": [0, 11],
                  "range_y": [0, 9], "horizontal_barriers": [],
                  "vertical_barriers": [[5, 0, 8]]},
        "llm_response": "Generated Path: [[3, 3], [8, 3]]",
    }
    records, audits = comparison.compare([case], {}, repeats=1, warmups=0)
    assert len(records) == 4
    assert all(not r["metrics"]["path_valid"] and r["length"] is None for r in records)
    assert audits[0]["status"] == "original_no_path_reconstruction_error"
    summaries = comparison.write_results(tmp_path, [case], {}, records, audits, 1, 0, 42)
    assert all(s["valid_path_ratio"] == 0 for s in summaries)
    assert all(s["relative_path_length_percent"] is None for s in summaries)
