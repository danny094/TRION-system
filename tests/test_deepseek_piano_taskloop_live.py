"""DeepSeek PIANO task-loop live tests against the Admin API container.

Der Backend-Livetest prueft NDJSON und Error-Mapping; diese Datei prueft
natuerliche Fragen gegen Routing, Toolfamilie und Task-Loop-Gates.
Gleiche Gate-Variable, gleiche Provider-/Key-Pruefung: require_deepseek_backend()
wird direkt importiert statt dupliziert (Konsolidierung statt zweiter
Konvention). Nicht erreichbarer Server -> skip.

Ambiguous-Cleanup wird nur bei risk_based/approval_first gefeuert.

Tool-Gruppen werden aus /api/tools abgeleitet. Lange Drift-Matrix:
TRION_ENABLE_DEEPSEEK_DRIFT_MATRIX=1.
"""
from __future__ import annotations

import os

import pytest

from tests.p11_live_http import get_json, post_chat_events
from tests.test_deepseek_backend_live import assert_no_ollama_fallback, require_deepseek_backend

_CALL_LOG: list[dict] = []


@pytest.fixture
def live_chat() -> dict:
    return require_deepseek_backend()


def _by_type(events: list[dict], type_name: str) -> list[dict]:
    return [e for e in events if e.get("type") == type_name]


def _live_tools() -> list[dict]:
    payload = get_json("/api/tools", timeout=10)
    assert isinstance(payload.get("tools"), list), f"Ungueltiger /api/tools-Contract: {payload!r}"
    return [t for t in payload["tools"] if isinstance(t, dict) and t.get("name")]


def _readish(tool: dict) -> bool:
    text = f"{tool.get('name', '')} {tool.get('description', '')}".lower()
    if any(word in text for word in ("delete", "save", "update", "merge", "prune", "stop", "start")):
        return False
    return any(word in text for word in ("find", "get", "list", "read", "search", "recent", "stats", "load", "now"))


def _require_live_tools(family: str) -> set[str]:
    tools = _live_tools()
    if family == "time":
        selected = [t for t in tools if t.get("mcp_name") == "time-mcp" and _readish(t)]
    elif family == "workspace":
        selected = [t for t in tools if str(t.get("name", "")).startswith("workspace_") and _readish(t)]
    elif family == "memory":
        selected = [
            t for t in tools
            if t.get("mcp_name") == "memory-mcp"
            and not str(t.get("name", "")).startswith(("secret_", "workspace_", "skill_"))
            and _readish(t)
        ]
    else:
        selected = []
    names = {str(t.get("name")) for t in selected}
    if not names:
        pytest.skip(f"Keine {family}-Read-Tools im erfolgreichen /api/tools-Katalog gefunden.")
    return names


def _assert_contract_operation(events: list[dict]) -> None:
    traces = _by_type(events, "routing_trace")
    assert traces, "Kein routing_trace fuer die OperationContract-Beobachtung."
    assert str(traces[-1].get("operation") or ""), "Keine sanitisierte Contract-Operation sichtbar."


def _post_chat(*, conversation_id: str, text: str, model: str) -> list[dict]:
    print(f"\n[PIANO-Live-Call] conversation_id={conversation_id}")
    events = post_chat_events(
        provider="deepseek",
        model=model,
        conversation_id=conversation_id,
        messages=[{"role": "user", "content": text}],
    )
    assert_no_ollama_fallback(events)
    done = (_by_type(events, "done") or [{}])[-1]
    classifier = _by_type(events, "classifier_result")
    _CALL_LOG.append({
        "conversation_id": conversation_id, "text": text, "done_reason": done.get("done_reason"),
        "route": classifier[0].get("route") if classifier else None,
        "tool_call_count": len(_by_type(events, "tool_start")),
    })
    return events


def test_piano_time_question_routing_is_observable(live_chat):
    _require_live_tools("time")
    events = _post_chat(conversation_id="piano-time", text="Wie spät ist es gerade ungefähr?", model=live_chat["model"])
    assert _by_type(events, "classifier_result"), "Kein classifier_result -- Pipeline-Stufe fehlt."
    assert _by_type(events, "done")[-1].get("done_reason") == "stop"
    tool_calls = _by_type(events, "tool_start")
    assert tool_calls, "Time-Tool ist live, aber keine Toolauswahl fuer eine Zeitfrage erfolgt."
    _assert_contract_operation(events)


def test_piano_home_synonym_question_routes_to_orchestrator(live_chat):
    events = _post_chat(conversation_id="piano-home", text="Was läuft gerade zuhause?", model=live_chat["model"])
    classifier = _by_type(events, "classifier_result")
    assert classifier, "Kein classifier_result -- Pipeline-Stufe fehlt."
    assert classifier[0].get("safety_level") != "block", "Home-Synonym-Frage wurde faelschlich hart geblockt."
    assert classifier[0].get("route") == "needs_orchestrator", f"Erwartete needs_orchestrator, bekam {classifier[0].get('route')!r}."
    assert _by_type(events, "done")[-1].get("done_reason") == "stop"


def test_piano_workspace_read_question_emits_contract_bound_tool_activity(live_chat):
    _require_live_tools("workspace")
    events = _post_chat(
        conversation_id="piano-workspace", model=live_chat["model"],
        text="Kannst du kurz prüfen, ob es im Workspace eine status.txt gibt?",
    )
    tool_calls = _by_type(events, "tool_start")
    assert tool_calls, "Workspace-Read-Tools sind live, aber die Leseanfrage waehlt kein Tool."
    _assert_contract_operation(events)


def test_piano_memory_context_question_is_observable(live_chat):
    _require_live_tools("memory")
    events = _post_chat(conversation_id="piano-memory", text="Was weißt du noch über unser P10.1 Thema?", model=live_chat["model"])
    assert _by_type(events, "classifier_result"), "Kein classifier_result -- Pipeline-Stufe fehlt."
    assert _by_type(events, "done")[-1].get("done_reason") == "stop"
    _assert_contract_operation(events)
    content = "".join(str(e.get("content") or "") for e in events if e.get("type") in {"content", "final_content"})
    assert content.strip(), "Leere Antwort auf eine Memory-Kontext-Frage."


def test_piano_ambiguous_cleanup_prompt_is_gated_or_skipped(live_chat):
    profile = get_json("/api/settings/autonomy/profile", timeout=10)
    mode = str((profile.get("mapped_runtime") or {}).get("TASK_LOOP_APPROVAL_MODE") or "").lower()
    if mode not in {"risk_based", "approval_first"}:
        pytest.skip(
            f"Live TASK_LOOP_APPROVAL_MODE={mode or 'unbekannt'} gated NEEDS_CONFIRMATION-Tools nicht "
            "(docker-compose Default ist 'permissive'). Ambiguous-Cleanup-Prompt wird nicht gegen die "
            "Live-Instanz gefeuert."
        )
    events = _post_chat(conversation_id="piano-cleanup-ambiguous", text="Mach mal alles wieder sauber.", model=live_chat["model"])
    assert not _by_type(events, "tool_start"), "Tool wurde gestartet, obwohl der Schritt vor Ausfuehrung gegated sein sollte."
    states = _by_type(events, "task_loop_state")
    gated = any(
        s.get("state") == "waiting" and s.get("stop_reason") == "risk_gate_required"
        for s in states
    )
    assert gated, f"Keine WAITING/risk_gate_required-Gate gefunden in task_loop_state Events: {states!r}"


def test_piano_drift_probe_same_intent_three_phrasings(live_chat):
    full_matrix = str(os.environ.get("TRION_ENABLE_DEEPSEEK_DRIFT_MATRIX", "")).lower()
    if full_matrix not in {"1", "true", "yes", "on"}:
        pytest.skip("Set TRION_ENABLE_DEEPSEEK_DRIFT_MATRIX=1 for the three-call drift matrix.")
    variants = [
        "Was läuft zuhause?",
        "Welche Container sind gerade aktiv?",
        "Kannst du mal schauen, was im Home-Space läuft?",
    ]
    routes = []
    for index, text in enumerate(variants):
        events = _post_chat(conversation_id=f"piano-drift-{index}", text=text, model=live_chat["model"])
        classifier = _by_type(events, "classifier_result")
        assert classifier, f"Kein classifier_result fuer Variante {index}: {text!r}"
        routes.append(classifier[0].get("route"))
    print(f"\n[PIANO-Drift] routes={routes}")
    seen = set(routes)
    assert not ({"needs_orchestrator", "direct_to_thinking"} <= seen), (
        f"Drift gefunden: gleiche Absicht routet je nach Formulierung unterschiedlich: {routes!r}"
    )


def test_piano_diagnostic_summary(live_chat):
    if not _CALL_LOG:
        pytest.skip("Nur Vollsuite-Zusammenfassung: keine Live-Calls im aktuellen Pytest-Prozess.")
    print(f"\n[PIANO-Live-Summary] calls={len(_CALL_LOG)}")
    for entry in _CALL_LOG:
        print(f"[PIANO-Live-Summary] {entry}")
