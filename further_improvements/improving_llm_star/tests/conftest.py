"""Keep integration tests headless and offline."""

import os
from pathlib import Path
import socket

import pytest


os.environ["MPLBACKEND"] = "Agg"
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[2] / ".venv/matplotlib"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


@pytest.fixture(autouse=True)
def prevent_network_calls(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Network connections are disabled during offline tests.")

    monkeypatch.setattr(socket.socket, "connect", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
