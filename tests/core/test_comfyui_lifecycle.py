# -*- coding: utf-8 -*-
from types import SimpleNamespace

from src.core.tools import comfyui_tools


def test_managed_comfyui_stops_when_it_started_the_worker(monkeypatch):
    events = []

    monkeypatch.setattr(comfyui_tools, "_is_comfyui_running", lambda: False)
    monkeypatch.setattr(
        comfyui_tools,
        "_start_comfyui_process",
        lambda: events.append("start") or SimpleNamespace(pid=123),
    )
    monkeypatch.setattr(comfyui_tools, "_wait_for_ready", lambda timeout_sec: True)
    monkeypatch.setattr(
        comfyui_tools,
        "comfyui_stop",
        lambda force=False: events.append(("stop", force)) or '{"status":"stopped"}',
    )

    with comfyui_tools.managed_comfyui():
        events.append("use")

    assert events == ["start", "use", ("stop", False)]


def test_managed_comfyui_does_not_stop_existing_worker(monkeypatch):
    events = []

    monkeypatch.setattr(comfyui_tools, "_is_comfyui_running", lambda: True)
    monkeypatch.setattr(comfyui_tools, "_start_comfyui_process", lambda: events.append("start"))
    monkeypatch.setattr(
        comfyui_tools,
        "comfyui_stop",
        lambda force=False: events.append(("stop", force)) or '{"status":"stopped"}',
    )

    with comfyui_tools.managed_comfyui():
        events.append("use")

    assert events == ["use"]
