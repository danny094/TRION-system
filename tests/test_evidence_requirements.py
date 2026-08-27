from config.pipeline.grounding import get_grounding_auto_recovery_whitelist
from core.output.evidence_contracts import ClaimType, EvidenceClaim, GuardDecision
from core.output.evidence_requirements import decide_guard
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff, OutputEvidenceItem, OutputEvidenceState
from mcp.registry import MCPRegistry


def _claim(claim_type: ClaimType, user_text: str, truth_source: str) -> EvidenceClaim:
    return EvidenceClaim(claim_type=claim_type, user_text=user_text, required_truth_source=truth_source)


def test_runtime_hardware_requires_validated_evidence():
    decision = decide_guard(
        _claim(ClaimType.RUNTIME_HARDWARE, "Wie viel RAM ist frei?", "hardware_runtime_tool"),
        OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
    )
    assert decision == GuardDecision.EXPLICIT_UNKNOWN


def test_runtime_time_limits_validated_evidence_to_verified_items():
    decision = decide_guard(
        _claim(ClaimType.RUNTIME_TIME, "Wie viel Uhr ist es?", "time_runtime_tool"),
        OutputEvidenceHandoff(
            OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE,
            (OutputEvidenceItem({"utc_iso": "2026-05-19T16:17:07Z"}),),
        ),
    )
    assert decision == GuardDecision.LIMIT_TO_VERIFIED


def test_skill_inventory_does_not_allow_from_unrelated_available_tools():
    decision = decide_guard(
        _claim(ClaimType.SKILL_INVENTORY, "Welche Tools hast du?", "skill_or_tool_inventory"),
        OutputEvidenceHandoff(OutputEvidenceState.TASK_LOOP_INCOMPLETE),
    )
    assert decision == GuardDecision.EXPLICIT_UNKNOWN


def test_container_runtime_without_validated_evidence_is_unknown():
    decision = decide_guard(
        _claim(ClaimType.CONTAINER_RUNTIME, "Welche Container laufen?", "container_runtime_tool"),
        OutputEvidenceHandoff(OutputEvidenceState.COMPLETE_WITHOUT_VALIDATED_EVIDENCE),
    )
    assert decision == GuardDecision.EXPLICIT_UNKNOWN


def test_conceptual_analysis_does_not_require_runtime_evidence():
    decision = decide_guard(
        _claim(ClaimType.CONCEPTUAL_ANALYSIS, "Wie würdest du das bauen?", "none"),
        OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
    )
    assert decision == GuardDecision.ALLOW


def test_grounding_auto_recovery_whitelist_is_empty_by_default(monkeypatch):
    monkeypatch.delenv("GROUNDING_AUTO_RECOVERY_WHITELIST", raising=False)
    assert get_grounding_auto_recovery_whitelist() == []


def test_registry_detection_rules_are_disabled_by_default():
    registry = MCPRegistry(type("Hub", (), {"_tool_definitions": {}, "_tools_cache": {}, "_transports": {}})())
    assert registry.detection_rules() == ""
