"""D1 + P10 Guardrail-Tests für core.routing_frame.builder.build_routing_frame.

D1: Persistente Phrasen aus execution_mode_signals_v2.csv müssen loop auslösen.
    (PIANO 1.0 D1-Fix, 2026-06-11 — ausgelagert aus test_routing_frame_builder.py,
    Doc 07 Zeilenlimit)
P10/T2: build_routing_frame enthält requested_operation_family + vollständige
    source_signals-Felder nach Signal-Layer-Erweiterung.
"""

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.routing_frame.builder import build_routing_frame


def _classifier(
    category: Category = Category.INFORMATION,
    *,
    needs_orchestrator: bool = False,
    route: Route | None = None,
    confidence: float = 0.9,
) -> ClassifierResult:
    return ClassifierResult(
        category=category,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=needs_orchestrator,
        confidence=confidence,
        route=route or (Route.NEEDS_ORCHESTRATOR if needs_orchestrator else Route.DIRECT_TO_THINKING),
        matched_pattern="test",
        reason="test",
    )


def _tool(name: str) -> dict:
    return {"name": name, "capability_domain": "general", "capability_operation": "read"}


# --- D1: persistent phrases from execution_mode_signals_v2.csv trigger loop mode ---
# Regel 6 Regressionstest: ohne detect_loop_signals würden diese Phrasen als
# direct_answer klassifiziert — nicht als loop.


def test_d1_persistent_phrase_taglich_triggers_loop_mode():
    frame = build_routing_frame(
        "Prüfe täglich die Fehlerlogs und sende einen Bericht.",
        _classifier(Category.TOOL, needs_orchestrator=True),
    )
    assert frame["execution_mode"] == "loop", (
        "persistent phrase 'täglich' must trigger execution_mode=loop via D1 CSV"
    )
    assert frame["source_signals"]["loop_markers"] is True


def test_d1_persistent_phrase_every_day_triggers_loop_mode():
    frame = build_routing_frame(
        "Run the summary every day and send it to me.",
        _classifier(Category.TOOL, needs_orchestrator=True),
    )
    assert frame["execution_mode"] == "loop", (
        "persistent phrase 'every day' must trigger execution_mode=loop via D1 CSV"
    )


def test_d1_non_persistent_phrase_does_not_trigger_loop():
    frame = build_routing_frame(
        "Erklaere mir das Konzept.",
        _classifier(),
    )
    assert frame["execution_mode"] != "loop", (
        "non-persistent phrase must not trigger loop mode"
    )


# --- source_signals completeness ---


def test_source_signals_contains_all_required_keys():
    frame = build_routing_frame(
        "Starte den Container.",
        _classifier(Category.TOOL, needs_orchestrator=True),
        selected_tool_details=[_tool("container_inspect")],
    )
    signals = frame["source_signals"]
    assert "classifier" in signals
    assert "live_claim" in signals
    assert "dialogue_signal" in signals
    assert "tool_counts" in signals
    assert "loop_markers" in signals
    assert "repeat_count" in signals


# ---------------------------------------------------------------------------
# P10: T2 — build_routing_frame enthält requested_operation_family
# ---------------------------------------------------------------------------


def test_build_routing_frame_contains_requested_operation_family_key():
    """T2a: Rückgabe-Dict enthält Key 'requested_operation_family'."""
    frame = build_routing_frame("Was ist die CPU-Auslastung?", _classifier())
    assert "requested_operation_family" in frame


def test_build_routing_frame_requested_operation_family_is_str():
    """T2b: requested_operation_family ist ein str (auch wenn leer)."""
    frame = build_routing_frame("Hallo!", _classifier(Category.SMALLTALK))
    assert isinstance(frame["requested_operation_family"], str)


def test_build_routing_frame_source_signals_unchanged():
    """T2c: source_signals enthält weiter live_claim, dialogue_signal, loop_markers."""
    frame = build_routing_frame("Wie viel Uhr ist es?", _classifier())
    src = frame["source_signals"]
    assert "live_claim" in src
    assert "dialogue_signal" in src
    assert "loop_markers" in src
    assert "repeat_count" in src
    assert "home_scope_verified" in src
    assert "self_context_present" in src


def test_build_routing_frame_no_behaviour_change_for_existing_fields():
    """T2d: Bestehende Frame-Felder (intent_kind, domain etc.) bleiben korrekt."""
    frame = build_routing_frame("Wie viel Uhr ist es?", _classifier())
    assert frame["intent_kind"] != ""
    assert frame["domain"] != ""
    assert frame["evidence_need"] != ""
    assert frame["execution_mode"] != ""
