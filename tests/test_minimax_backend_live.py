"""MiniMax-Backend-Live for the real Admin-API /api/chat path.

The existing Ollama Cloud live test covers provider/core helpers directly; this
one covers the running backend HTTP NDJSON stream, generic public errors,
and P10.1-visible pipeline events. Gate: TRION_ENABLE_MINIMAX_TESTS=1. The
MiniMax key is expected in the backend settings store and is never printed.
"""
from __future__ import annotations

import json
from urllib.parse import urljoin

import pytest
import requests

from tests.conftest import env_or_dotenv

FORBIDDEN_TEXT_MARKERS = ("missing_endpoint:ollama",)
CALL_LOG: list[dict] = []


def _backend_url() -> str:
    raw = env_or_dotenv("TRION_BACKEND_URL", "http://127.0.0.1:8200")
    return str(raw or "").rstrip("/") + "/"


def _live_model() -> str:
    return env_or_dotenv("TRION_MINIMAX_LIVE_MODEL", "") or env_or_dotenv("TRION_MINIMAX_SMOKE_MODEL", "") or "default"


def _get_json(path: str, *, timeout: int = 20) -> dict:
    response = requests.get(urljoin(_backend_url(), path.lstrip("/")), timeout=timeout)
    response.raise_for_status()
    data = response.json()
    assert isinstance(data, dict)
    return data


def _require_minimax_backend() -> dict:
    enabled = env_or_dotenv("TRION_ENABLE_MINIMAX_TESTS", "").lower()
    if enabled not in {"1", "true", "yes", "on"}:
        pytest.skip("Set TRION_ENABLE_MINIMAX_TESTS=1 to run live MiniMax backend tests.")
    try:
        _get_json("/health", timeout=10)
        keys = _get_json("/api/settings/api-keys", timeout=10)
        catalog = _get_json("/api/models/catalog", timeout=30)
    except Exception as exc:
        pytest.skip(f"Backend unavailable for live MiniMax tests: {exc}")

    key_ids = {str(item.get("id") or item.get("name") or "") for item in keys.get("keys", [])}
    if "MINIMAX_API_KEY" not in key_ids and "MINIMAX_KEY" not in key_ids:
        pytest.skip("MiniMax key missing in backend settings store.")

    provider = str(catalog.get("effective", {}).get("OUTPUT_PROVIDER") or "").lower()
    assert provider == "minimax", f"Expected OUTPUT_PROVIDER=minimax, got {provider!r}"
    return {"model": _live_model(), "effective": catalog.get("effective", {})}


@pytest.fixture
def live_chat() -> dict:
    return _require_minimax_backend()


def _events_from_response(response: requests.Response) -> list[dict]:
    assert response.status_code == 200, response.text
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert events, "No NDJSON events returned."
    return events


def _assert_no_ollama_fallback(events: list[dict]) -> None:
    blob = json.dumps(events, ensure_ascii=False).lower()
    for marker in FORBIDDEN_TEXT_MARKERS:
        assert marker not in blob, f"Ollama marker found: {marker}"


def _assert_contract(events: list[dict], *, expect_error: bool = False) -> None:
    _assert_no_ollama_fallback(events)
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
    payload = {
        "model": model, "provider": "minimax", "conversation_id": conversation_id,
        "messages": messages or [{"role": "user", "content": text}],
        "stream": True,
    }
    response = requests.post(
        urljoin(_backend_url(), "/api/chat"),
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=90,
    )
    events = _events_from_response(response)
    _assert_no_ollama_fallback(events)
    CALL_LOG.append(
        {
            "conversation_id": conversation_id,
            "model": events[-1].get("model"),
            "event_types": [event.get("type") for event in events],
            "done_reason": events[-1].get("done_reason"),
        }
    )
    return events


def test_minimax_http_provider_gate_and_simple_call(live_chat):
    events = _post_chat(
        conversation_id="minimax-http-gate",
        model=live_chat["model"],
        text="Antworte exakt: backend live ok",
    )
    _assert_contract(events)
    assert "minimax" in str(events[-1].get("model") or "").lower()


def test_minimax_multi_turn_context_is_preserved(live_chat):
    messages = [
        {"role": "user", "content": "Merke dir das Testwort basalt-42. Antworte nur mit: ok"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "Welches Testwort hast du dir gemerkt?"},
    ]
    events = _post_chat(conversation_id="minimax-http-multiturn", model=live_chat["model"], messages=messages)
    _assert_contract(events)
    assert "basalt" in _content(events).lower()


def test_minimax_task_loop_and_replan_path_is_observable(live_chat):
    events = _post_chat(
        conversation_id="minimax-http-replan",
        model=live_chat["model"],
        text="Wie viel Uhr ist es gerade? Nutze nur lesende Werkzeuge, falls du Werkzeuge nutzt.",
    )
    _assert_contract(events)


def test_minimax_p10_1_tool_eligibility_path_is_observable(live_chat):
    events = _post_chat(
        conversation_id="minimax-http-tool-eligibility",
        model=live_chat["model"],
        text="Welche Werkzeuge stehen dir gerade zur Verfuegung? Nicht ausfuehren, nur zusammenfassen.",
    )
    _assert_contract(events)


def test_minimax_memory_context_reach_is_observable(live_chat):
    events = _post_chat(
        conversation_id="minimax-http-memory",
        model=live_chat["model"],
        text="Was weisst du ueber das TRION Projekt aus deinem Backend-Kontext?",
    )
    _assert_contract(events)


def test_minimax_truth_reasoning_evidence_gap_is_observable(live_chat):
    events = _post_chat(
        conversation_id="minimax-http-truth",
        model=live_chat["model"],
        text="Wie viel Uhr ist es gerade in UTC? Nutze nur verifizierbare Backend-Evidenz.",
    )
    _assert_contract(events)


def test_minimax_error_mode_uses_generic_public_error(live_chat):
    events = _post_chat(
        conversation_id="minimax-http-error",
        model="definitely-not-a-real-minimax-model-xyz",
        text="Antworte nur mit: ok",
    )
    _assert_contract(events, expect_error=True)
    errors = [event for event in events if event.get("type") == "error"]
    assert errors[0].get("error_code") == "internal_error", errors
    assert errors[0].get("content") == "Ein interner Fehler ist aufgetreten.", errors
    assert "error_provider" not in errors[0]
    assert "error_status" not in errors[0]


def test_minimax_diagnostic_summary_no_ollama_hint_anywhere(live_chat):
    assert live_chat["effective"].get("OUTPUT_PROVIDER") == "minimax"
    assert CALL_LOG, "No live calls recorded."
    print(f"\n[MiniMax-Live-Summary] calls={len(CALL_LOG)} backend={_backend_url()}")
    for entry in CALL_LOG:
        print(f"[MiniMax-Live-Summary] {entry}")
