from config.pipeline.grounding import get_grounding_auto_recovery_whitelist
from core.output.evidence_contracts import ClaimType, EvidenceBundle, EvidenceClaim, GuardDecision
from core.output.evidence_requirements import decide_guard
from mcp.registry import MCPRegistry


def _claim(claim_type: ClaimType, user_text: str, truth_source: str) -> EvidenceClaim:
    return EvidenceClaim(claim_type=claim_type, user_text=user_text, required_truth_source=truth_source)


def test_runtime_hardware_requires_live_matching_tool_evidence():
    decision = decide_guard(
        _claim(ClaimType.RUNTIME_HARDWARE, "Wie viel RAM ist frei?", "hardware_runtime_tool"),
        EvidenceBundle(
            grounded_tool_results=[{"tool_name": "get_system_info", "facts": {"ram": "12 GB"}}],
            available_tool_details=[],
        ),
    )
    assert decision == GuardDecision.EXPLICIT_UNKNOWN


def test_runtime_time_allows_live_time_tool_evidence():
    decision = decide_guard(
        _claim(ClaimType.RUNTIME_TIME, "Wie viel Uhr ist es?", "time_runtime_tool"),
        EvidenceBundle(
            grounded_tool_results=[{"tool_name": "time_now", "facts": {"utc_iso": "2026-05-19T16:17:07Z"}}],
            available_tool_details=[
                {"name": "time_now", "source": "time-mcp", "description": "Get current UTC time"}
            ],
        ),
    )
    assert decision == GuardDecision.ALLOW


def test_skill_inventory_does_not_allow_from_unrelated_available_tools():
    decision = decide_guard(
        _claim(ClaimType.SKILL_INVENTORY, "Welche Tools hast du?", "skill_or_tool_inventory"),
        EvidenceBundle(
            available_tools=["time_now"],
            selected_tools=["time_now"],
            available_tool_details=[{"name": "time_now", "source": "time-mcp", "description": "Get current UTC time"}],
        ),
    )
    assert decision == GuardDecision.EXPLICIT_UNKNOWN


def test_container_runtime_allows_grounded_live_container_tool():
    decision = decide_guard(
        _claim(ClaimType.CONTAINER_RUNTIME, "Welche Container laufen?", "container_runtime_tool"),
        EvidenceBundle(
            grounded_tool_results=[{"tool_name": "container_list", "facts": {"count": 2}}],
            available_tool_details=[
                {"name": "container_list", "source": "container-commander", "description": "List running containers"}
            ],
        ),
    )
    assert decision == GuardDecision.ALLOW


def test_container_capability_question_allows_verified_home_context_scope():
    decision = decide_guard(
        _claim(
            ClaimType.CONTAINER_RUNTIME,
            "Was kannst du mit dem Container hier machen?",
            "container_runtime_tool",
        ),
        EvidenceBundle(
            home_context={
                "verified": True,
                "available_capability_classes": ["container_inspect"],
            },
        ),
    )
    assert decision == GuardDecision.ALLOW


def test_grounding_auto_recovery_whitelist_is_empty_by_default(monkeypatch):
    monkeypatch.delenv("GROUNDING_AUTO_RECOVERY_WHITELIST", raising=False)
    assert get_grounding_auto_recovery_whitelist() == []


def test_registry_detection_rules_are_disabled_by_default():
    registry = MCPRegistry(type("Hub", (), {"_tool_definitions": {}, "_tools_cache": {}, "_transports": {}})())
    assert registry.detection_rules() == ""
