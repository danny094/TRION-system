"""Bounded DeepSeek trace for natural container-question paraphrases.

This diagnostic suite requires both DeepSeek live gates and refuses unbounded
Task-Loop settings. It compares controlled decisions and counts, not answer
wording, internal IDs, tool metadata, arguments or artifact contents.
"""
from __future__ import annotations

import json
import os

import pytest
from tests.p11_live_http import get_json, post_chat_events
from tests.test_deepseek_backend_live import assert_no_ollama_fallback, require_deepseek_backend

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
    enabled = str(os.environ.get("TRION_ENABLE_PIANO_TRACE_TESTS", "")).lower()
    if enabled not in {"1", "true", "yes", "on"}:
        pytest.skip("Set TRION_ENABLE_PIANO_TRACE_TESTS=1 for the bounded PIANO trace.")
    live = require_deepseek_backend()
    runtime = get_json("/api/settings/sequential/runtime", timeout=10)
    max_replans = int(_effective_value(runtime, "TASK_LOOP_MAX_REPLANS") or 0)
    max_steps = int(_effective_value(runtime, "TASK_LOOP_MAX_STEPS") or 0)
    loop_detection = bool(_effective_value(runtime, "TASK_LOOP_LOOP_DETECTION_ENABLE"))
    assert max_replans == 1, f"Trace requires TASK_LOOP_MAX_REPLANS=1, got {max_replans}."
    assert max_steps == 5, f"Trace requires TASK_LOOP_MAX_STEPS=5, got {max_steps}."
    assert loop_detection, "Trace requires TASK_LOOP_LOOP_DETECTION_ENABLE=true."
    return {**live, "runtime": {"max_replans": max_replans, "max_steps": max_steps}}


def _post(prompt: str, index: int, model: str) -> list[dict]:
    events = post_chat_events(
        provider="deepseek",
        model=model,
        conversation_id=f"piano-trace-{index}",
        messages=[{"role": "user", "content": prompt}],
        timeout=180,
    )
    assert_no_ollama_fallback(events)
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


def test_deepseek_piano_replan_trace(trace_backend):
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
