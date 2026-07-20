"""Bounded MiniMax trace for natural container-question paraphrases.

This diagnostic suite requires both MiniMax live gates and refuses unbounded
Task-Loop settings. It compares controlled decisions and counts, not answer
wording, internal IDs, tool metadata, arguments or artifact contents.
"""
from __future__ import annotations

import json

import pytest
import requests

from tests.conftest import env_or_dotenv
from tests.test_minimax_backend_live import (
    _assert_no_ollama_fallback,
    _backend_url,
    _require_minimax_backend,
)

PROMPTS = (
    "Was läuft zuhause?",
    "Welche Container sind gerade aktiv?",
    "Kannst du mal schauen, was im Home-Space läuft?",
)


def _effective_value(payload: dict, key: str):
    raw = (payload.get("effective") or {}).get(key)
    return raw.get("value") if isinstance(raw, dict) else raw


@pytest.fixture(scope="module")
def trace_backend() -> dict:
    enabled = env_or_dotenv("TRION_ENABLE_PIANO_TRACE_TESTS", "").lower()
    if enabled not in {"1", "true", "yes", "on"}:
        pytest.skip("Set TRION_ENABLE_PIANO_TRACE_TESTS=1 for the bounded PIANO trace.")
    live = _require_minimax_backend()
    response = requests.get(f"{_backend_url()}api/settings/sequential/runtime", timeout=10)
    response.raise_for_status()
    runtime = response.json()
    max_replans = int(_effective_value(runtime, "TASK_LOOP_MAX_REPLANS") or 0)
    max_steps = int(_effective_value(runtime, "TASK_LOOP_MAX_STEPS") or 0)
    loop_detection = bool(_effective_value(runtime, "TASK_LOOP_LOOP_DETECTION_ENABLE"))
    assert 1 <= max_replans <= 3, f"Trace requires finite TASK_LOOP_MAX_REPLANS 1..3, got {max_replans}."
    assert 1 <= max_steps <= 5, f"Trace requires TASK_LOOP_MAX_STEPS 1..5, got {max_steps}."
    assert loop_detection, "Trace requires TASK_LOOP_LOOP_DETECTION_ENABLE=true."
    return {**live, "runtime": {"max_replans": max_replans, "max_steps": max_steps}}


def _post(prompt: str, index: int, model: str) -> list[dict]:
    payload = {
        "model": model,
        "provider": "minimax",
        "conversation_id": f"piano-trace-{index}",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    response = requests.post(
        f"{_backend_url()}api/chat",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=180,
    )
    response.raise_for_status()
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    _assert_no_ollama_fallback(events)
    assert events and events[-1].get("type") == "done", events
    return events


def _summary(prompt: str, events: list[dict]) -> dict:
    classifier = next((event for event in events if event.get("type") == "classifier_result"), {})
    initial = next((event for event in events if event.get("type") == "thinking_plan"), {})
    routing = next((event for event in events if event.get("type") == "routing_trace"), {})
    replans = [event for event in events if event.get("type") == "replan_trace" and event.get("phase") == "replan"]
    states = [event for event in events if event.get("type") == "task_loop_state"]
    return {
        "prompt": prompt,
        "route": classifier.get("route"),
        "safety_level": classifier.get("safety_level"),
        "operation": routing.get("operation"),
        "initial_step_count": initial.get("step_count"),
        "tool_call_count": len([event for event in events if event.get("type") == "tool_start"]),
        "replans": replans,
        "state_transitions": [
            {
                "state": event.get("state"),
                "stop_reason": event.get("stop_reason"),
                "replan_count": event.get("replan_count"),
                "step_index": event.get("step_index"),
                "total_steps": event.get("total_steps"),
            }
            for event in states
        ],
        "done_reason": events[-1].get("done_reason"),
    }


def test_minimax_piano_replan_trace(trace_backend):
    summaries = [
        _summary(prompt, _post(prompt, index, trace_backend["model"]))
        for index, prompt in enumerate(PROMPTS)
    ]
    print("\n[PIANO-REPLAN-TRACE] " + json.dumps({
        "runtime": trace_backend["runtime"],
        "summaries": summaries,
    }, ensure_ascii=False, indent=2))

    assert {item["route"] for item in summaries} == {"needs_orchestrator"}
    for item in summaries:
        assert item["safety_level"] != "block"
        assert len(item["replans"]) <= trace_backend["runtime"]["max_replans"]
        assert item["done_reason"] in {"stop", "blocked", "rejected"}
