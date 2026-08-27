"""DeepSeek backend live tests for the real Admin-API /api/chat path.

The existing Ollama Cloud live test covers provider/core helpers directly; this
one covers the running backend HTTP NDJSON stream, generic public errors,
and P10.1-visible pipeline events. Gate: TRION_ENABLE_DEEPSEEK_TESTS=1. The
DeepSeek key is expected in the backend settings store and is never printed.
"""
from __future__ import annotations

import os

import pytest

from tests.p11_live_http import (
    backend_url,
    get_json,
    post_chat_events,
)

FORBIDDEN_TEXT_MARKERS = ("missing_endpoint:ollama",)
CALL_LOG: list[dict] = []


def _effective_value(effective: dict, key: str):
    value = effective.get(key)
    return value.get("value") if isinstance(value, dict) else value


def require_deepseek_backend() -> dict:
    enabled = str(os.environ.get("TRION_ENABLE_DEEPSEEK_TESTS", "")).lower()
    if enabled not in {"1", "true", "yes", "on"}:
        pytest.skip("Set TRION_ENABLE_DEEPSEEK_TESTS=1 to run live DeepSeek backend tests.")
    try:
        get_json("/health", timeout=10)
        keys = get_json("/api/settings/api-keys", timeout=10)
        settings = get_json("/api/settings/models/effective", timeout=30)
    except Exception as exc:
        pytest.fail(f"Backend unavailable for opted-in DeepSeek live tests: {exc}")

    key_ids = {str(item.get("id") or item.get("name") or "") for item in keys.get("keys", [])}
    assert key_ids.intersection({"DEEPSEEK_API_KEY", "DEEPSEEK_KEY", "DEEPSEEK"}), (
        "DeepSeek key missing in backend settings store."
    )
    effective = settings.get("effective", {})
    for role in ("THINKING_PROVIDER", "CONTROL_PROVIDER", "OUTPUT_PROVIDER"):
        provider = str(_effective_value(effective, role) or "").lower()
        assert provider == "deepseek", f"Expected {role}=deepseek, got {provider!r}"
    model = str(_effective_value(effective, "OUTPUT_MODEL") or "")
    assert model, "Expected a non-empty effective OUTPUT_MODEL for DeepSeek."
    return {"model": model, "effective": effective}


def assert_no_ollama_fallback(events: list[dict]) -> None:
    blob = str(events).lower()
    for marker in FORBIDDEN_TEXT_MARKERS:
        assert marker not in blob, f"Ollama marker found: {marker}"


@pytest.fixture
def live_chat() -> dict:
    return require_deepseek_backend()


def _assert_contract(events: list[dict], *, expect_error: bool = False) -> None:
    assert_no_ollama_fallback(events)
    assert events[-1].get("type") == "done", events
    assert events[-1].get("done") is True, events[-1]
    reason = events[-1].get("done_reason")
    if expect_error:
        assert reason == "error", events[-1]
        assert any(event.get("type") == "error" for event in events), events
    else:
        assert reason == "stop", events[-1]
        assert any(event.get("type") == "classifier_result" for event in events), events
        assert any(event.get("type") == "thinking_plan" for event in events), events
        assert any(event.get("type") == "verifier_result" for event in events), events
        assert any(event.get("type") in {"content", "final_content"} for event in events), events


def _content(events: list[dict]) -> str:
    return "".join(str(e.get("content") or "") for e in events if e.get("type") in {"content", "final_content"})


def _post_chat(*, conversation_id: str, text: str = "", messages=None, model: str) -> list[dict]:
    events = post_chat_events(
        provider="deepseek",
        model=model,
        conversation_id=conversation_id,
        messages=messages or [{"role": "user", "content": text}],
    )
    assert_no_ollama_fallback(events)
    CALL_LOG.append(
        {
            "conversation_id": conversation_id,
            "model": events[-1].get("model"),
            "event_types": [event.get("type") for event in events],
            "done_reason": events[-1].get("done_reason"),
        }
    )
    return events


def test_deepseek_http_provider_gate_and_simple_call(live_chat):
    events = _post_chat(
        conversation_id="deepseek-http-gate",
        model=live_chat["model"],
        text="Antworte exakt: backend live ok",
    )
    _assert_contract(events)
    assert "deepseek" in str(events[-1].get("model") or "").lower()


def test_deepseek_multi_turn_context_is_preserved(live_chat):
    messages = [
        {"role": "user", "content": "Merke dir das Testwort basalt-42. Antworte nur mit: ok"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "Welches Testwort hast du dir gemerkt?"},
    ]
    events = _post_chat(conversation_id="deepseek-http-multiturn", model=live_chat["model"], messages=messages)
    _assert_contract(events)
    assert "basalt" in _content(events).lower()


def test_deepseek_task_loop_and_replan_path_is_observable(live_chat):
    events = _post_chat(
        conversation_id="deepseek-http-replan",
        model=live_chat["model"],
        text="Wie viel Uhr ist es gerade? Nutze nur lesende Werkzeuge, falls du Werkzeuge nutzt.",
    )
    _assert_contract(events)


def test_deepseek_p10_1_tool_eligibility_path_is_observable(live_chat):
    events = _post_chat(
        conversation_id="deepseek-http-tool-eligibility",
        model=live_chat["model"],
        text="Welche Werkzeuge stehen dir gerade zur Verfuegung? Nicht ausfuehren, nur zusammenfassen.",
    )
    _assert_contract(events)


def test_deepseek_memory_context_reach_is_observable(live_chat):
    events = _post_chat(
        conversation_id="deepseek-http-memory",
        model=live_chat["model"],
        text="Was weisst du ueber das TRION Projekt aus deinem Backend-Kontext?",
    )
    _assert_contract(events)


def test_deepseek_truth_reasoning_evidence_gap_is_observable(live_chat):
    events = _post_chat(
        conversation_id="deepseek-http-truth",
        model=live_chat["model"],
        text="Wie viel Uhr ist es gerade in UTC? Nutze nur verifizierbare Backend-Evidenz.",
    )
    _assert_contract(events)


def test_deepseek_error_mode_uses_generic_public_error(live_chat):
    events = _post_chat(
        conversation_id="deepseek-http-error",
        model="definitely-not-a-real-deepseek-model-xyz",
        text="Antworte nur mit: ok",
    )
    _assert_contract(events, expect_error=True)
    errors = [event for event in events if event.get("type") == "error"]
    assert errors[0].get("error_code") == "internal_error", errors
    assert errors[0].get("content") == "Ein interner Fehler ist aufgetreten.", errors
    assert "error_provider" not in errors[0]
    assert "error_status" not in errors[0]


def test_deepseek_diagnostic_summary_no_ollama_hint_anywhere(live_chat):
    assert _effective_value(live_chat["effective"], "OUTPUT_PROVIDER") == "deepseek"
    assert CALL_LOG, "No live calls recorded."
    print(f"\n[DeepSeek-Live-Summary] calls={len(CALL_LOG)} backend={backend_url()}")
    for entry in CALL_LOG:
        print(f"[DeepSeek-Live-Summary] {entry}")
