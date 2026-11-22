"""Offline integration checks: real dependencies, fixed answers, no API calls."""

import copy
import importlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "progress_measurement", ROOT / "experiments/measure_waypoint_progress.py"
)
measurement = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(measurement)


@pytest.mark.parametrize("name", [
    "openai", "inquirer", "shapely", "matplotlib", "numpy", "transformers", "torch",
])
def test_required_dependency_imports(name):
    importlib.import_module(name)


def test_real_package_and_tensor_operation():
    import llmastar
    import torch
    from llmastar.pather import AStar, LLMAStar
    from transformers import pipeline

    assert Path(llmastar.__file__).resolve().parent == ROOT / "llmastar"
    assert callable(AStar) and callable(LLMAStar) and callable(pipeline)
    assert torch.tensor([1, 2, 3]).sum().item() == 6


def test_installed_measurements_match_isolated_results(monkeypatch):
    monkeypatch.setattr(measurement, "BACKEND", "installed")
    records = measurement.measure()
    previous = json.loads((ROOT / "experiments/results/waypoint_progress/measurement.json").read_text())
    assert len(records) == 18
    for actual, expected in zip(records, previous["records"]):
        assert actual["case"] == expected["case"]
        assert actual["alpha"] == expected["alpha"]
        # Serialized tuples become lists, so compare JSON-normalized records.
        assert json.loads(json.dumps(actual["result"])) == expected["result"]
        assert json.loads(json.dumps(actual["waypoint_progress"])) == expected["waypoint_progress"]


def test_actual_plotting_saves_a_path_without_network(monkeypatch, tmp_path):
    from llmastar.pather.llm_a_star import llm_a_star as planner_module
    import matplotlib.pyplot as plt

    answer = 'Generated Path: [[3, 3], [5, 5], [8, 8]]'
    monkeypatch.setattr(planner_module, "ChatGPT", lambda **kwargs: measurement.OfflineModel(answer))
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)
    query = {
        "start": [3, 3], "goal": [8, 8], "range_x": [0, 31], "range_y": [0, 21],
        "horizontal_barriers": [], "vertical_barriers": [],
    }
    image = tmp_path / "search.png"
    planner = planner_module.LLMAStar(track_progress=True)
    result = planner.searching(copy.deepcopy(query), filepath=str(image))
    assert image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert result["length"] == pytest.approx(5 * 2 ** 0.5)
    assert sum(s["expansions"] for s in planner.waypoint_progress) == result["operation"]
    assert planner.model.calls == 1
