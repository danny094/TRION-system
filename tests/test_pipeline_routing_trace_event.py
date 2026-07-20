import json

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.pipeline.routing_trace import routing_trace_event
from core.routing_frame.builder import build_routing_frame


def _classifier() -> ClassifierResult:
    return ClassifierResult(
        category=Category.TOOL,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=True,
        confidence=0.9,
        route=Route.NEEDS_ORCHESTRATOR,
        matched_pattern="test",
        reason="test",
    )


def _frame(text: str) -> dict:
    return build_routing_frame(text, _classifier())


def test_same_allowed_meaning_projection_has_same_fingerprint():
    base = _frame("Läuft der Container trion-home?")
    changed_sensitive = dict(base)
    changed_sensitive["operation_contract"] = {
        **base["operation_contract"],
        "target": "secret-target",
        "scope_lock": "secret-scope",
    }
    signals = dict(base["source_signals"])
    meaning = dict(signals["meaning_shadow_trace"])
    meaning["target_candidates"] = ["secret-target"]
    meaning["scope_candidates"] = ["secret-scope"]
    meaning["provenance"] = {
        "predicate": {"source": "secret", "confidence": 1.0, "span": "private raw text"}
    }
    signals["meaning_shadow_trace"] = meaning
    changed_sensitive["source_signals"] = signals

    assert routing_trace_event(base)["meaning_fingerprint"] == routing_trace_event(changed_sensitive)["meaning_fingerprint"]


def test_different_allowed_meaning_projection_changes_fingerprint():
    status = routing_trace_event(_frame("Läuft der Container trion-home?"))
    logs = routing_trace_event(_frame("Zeige mir die Logs vom Container trion-home."))

    assert status["meaning_fingerprint"] != logs["meaning_fingerprint"]


def test_routing_trace_exposes_contract_projection_without_raw_values():
    event = routing_trace_event(_frame("Läuft der Container trion-home?"))
    serialized = json.dumps(event, ensure_ascii=False)

    assert event["type"] == "routing_trace"
    assert "operation_contract_fingerprint" not in event
    assert event["operation"] == "list"
    assert event["allowed_operations"] == ["list"]
    assert event["allowed_transitions"] == []
    assert event["required_evidence"] == ["runtime_status"]
    assert event["target_bound"] is True
    assert event["scope_lock_present"] is True
    assert "trion-home" not in serialized
    assert "Läuft" not in serialized
    assert "private-container" not in serialized
    assert "SECRET_SENTINEL" not in serialized


def test_routing_trace_exposes_sanitized_composite_transition_only():
    event = routing_trace_event(_frame("Welche Container laufen und zeige mir die Logs."))
    serialized = json.dumps(event, ensure_ascii=False)

    assert event["operation"] == "list"
    assert event["allowed_operations"] == ["list"]
    assert event["allowed_transitions"] == ["list->logs"]
    assert "container_list_logs" not in serialized
    assert "Welche Container" not in serialized
    assert "trion-home" not in serialized
    assert "SECRET_SENTINEL" not in serialized


def test_missing_contract_fails_closed_without_rawtext_fallback():
    event = routing_trace_event(
        {
            "requested_operation_family": "list",
            "source_signals": {
                "meaning_shadow_trace": {
                    "status": "ok",
                    "predicate": "runtime_state",
                    "theme": "container",
                }
            },
        }
    )

    assert "operation_contract_fingerprint" not in event
    assert event["operation"] == ""
    assert event["allowed_operations"] == []
    assert event["allowed_transitions"] == []
    assert event["required_evidence"] == []
    assert event["target_bound"] is False
    assert event["meaning_fingerprint"] == ""
