import asyncio
from dataclasses import fields
from inspect import signature

import pytest

from intelligence_modules.cim_policy import cim_policy_engine as cim
from mcp.tool_result_contracts import (
    MCPResultPresence,
    MCPToolCallStatus,
    MCPToolResultEnvelope,
    project_tool_result_wire_mapping,
)


class FakeHub:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    async def call_tool_async(self, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        return next(self.results)


def _policy_match(*, allows_chaining=False):
    return cim.PolicyMatch(
        pattern_id="test",
        trigger_category="test",
        confidence=1.0,
        action=cim.ActionType.RUN_SKILL,
        skill_scope=cim.SkillScope.STATELESS,
        safety_level=cim.SafetyLevel.LOW,
        requires_confirmation=False,
        allows_chaining=allows_chaining,
    )


def _decision(action, *, skill_name="demo", allows_chaining=False):
    return cim.CIMDecision(
        matched=True,
        action=action,
        skill_name=skill_name,
        policy_match=_policy_match(allows_chaining=allows_chaining),
    )


def _success():
    return MCPToolResultEnvelope(MCPToolCallStatus.SUCCESS)


def test_cim_facade_preserves_public_exports_and_signatures():
    expected_exports = {
        "SafetyLevel",
        "SkillScope",
        "ActionType",
        "PolicyMatch",
        "CIMDecision",
        "CIMPolicyEngine",
        "get_cim_engine",
        "reset_cim_engine",
        "process_cim",
        "execute_cim_decision",
    }
    assert all(hasattr(cim, name) for name in expected_exports)
    assert [field.name for field in fields(cim.PolicyMatch)] == [
        "pattern_id", "trigger_category", "confidence", "action", "skill_scope",
        "safety_level", "requires_confirmation", "allows_chaining",
        "derived_skill_name", "fallback_action",
    ]
    assert [field.name for field in fields(cim.CIMDecision)] == [
        "matched", "action", "skill_name", "requires_confirmation",
        "policy_match", "reason",
    ]
    assert tuple(signature(cim.CIMPolicyEngine).parameters) == ("policy_file",)
    assert tuple(signature(cim.CIMPolicyEngine.process).parameters) == (
        "self", "user_input", "available_skills",
    )
    assert tuple(signature(cim.process_cim).parameters) == (
        "user_input", "available_skills",
    )
    assert tuple(signature(cim.execute_cim_decision).parameters) == (
        "decision", "user_input", "hub",
    )


def test_execute_cim_decision_preserves_five_dispatches(monkeypatch):
    async def generated_code(user_input, skill_name, hub):
        return "generated-code"

    monkeypatch.setattr(cim, "_generate_skill_code", generated_code)
    hub = FakeHub([_success(), _success(), _success(), _success(), _success()])

    asyncio.run(cim.execute_cim_decision(
        _decision(cim.ActionType.FORCE_CREATE_SKILL, allows_chaining=True),
        "Berechne 7", hub,
    ))
    asyncio.run(cim.execute_cim_decision(
        _decision(cim.ActionType.FORCE_RUN_SKILL), "Berechne 7", hub,
    ))
    asyncio.run(cim.execute_cim_decision(
        _decision(cim.ActionType.RUN_SKILL), "Berechne 7", hub,
    ))
    asyncio.run(cim.execute_cim_decision(
        _decision(cim.ActionType.LIST_SKILLS), "Berechne 7", hub,
    ))

    assert hub.calls == [
        ("create_skill", {
            "name": "demo",
            "code": "generated-code",
            "description": "Auto-generated skill for: Berechne 7",
            "triggers": ["berechne"],
        }),
        ("run_skill", {"name": "demo", "args": {"n": 7}}),
        ("run_skill", {"name": "demo", "args": {"n": 7}}),
        ("run_skill", {"name": "demo", "args": {"n": 7}}),
        ("list_skills", {}),
    ]


@pytest.mark.parametrize(
    ("envelope", "expected_executed"),
    [
        (MCPToolResultEnvelope(MCPToolCallStatus.SUCCESS), True),
        (MCPToolResultEnvelope(
            MCPToolCallStatus.SUCCESS,
            structured_content_presence=MCPResultPresence.EMPTY,
            structured_content={},
        ), True),
        (MCPToolResultEnvelope(
            MCPToolCallStatus.SUCCESS,
            structured_content_presence=MCPResultPresence.VALUE,
            structured_content={"skills": ["demo"]},
        ), True),
        (MCPToolResultEnvelope(
            MCPToolCallStatus.TOOL_FAILURE,
            is_error_presence=MCPResultPresence.VALUE,
            is_error=True,
        ), False),
        (MCPToolResultEnvelope(
            MCPToolCallStatus.PROTOCOL_FAILURE,
            protocol_error={"code": -32603},
        ), False),
        (MCPToolResultEnvelope(
            MCPToolCallStatus.TRANSPORT_FAILURE,
            transport_diagnostic="offline",
        ), False),
    ],
    ids=["missing", "empty", "value", "tool", "protocol", "transport"],
)
def test_execute_cim_decision_projects_typed_result(envelope, expected_executed):
    hub = FakeHub([envelope])

    result = asyncio.run(cim.execute_cim_decision(
        _decision(cim.ActionType.LIST_SKILLS), "Liste Skills", hub,
    ))

    assert result["executed"] is expected_executed
    assert result["output"] == dict(project_tool_result_wire_mapping(envelope))
