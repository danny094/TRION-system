import container_commander_bundle_fakes  # noqa: F401
import bundle_dispatch  # noqa: E402

from core.task_loop.contracts import EvidenceArtifact
from core.task_loop.evidence_adapter import validated_evidence_artifacts
from core.task_loop.outcome_evaluator import OutcomeAction, evaluate
from core.task_loop.tool_execution_contracts import TaskStructuralValidationStatus
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from mcp.protocol_contracts import MCPTransportRequestOutcome, MCPTransportRequestStatus
from mcp.structural_validation_contracts import MCPStructuralValidationStatus
from mcp.structural_validator import validate_structured_output
from mcp.tool_result_contracts import project_tool_result_envelope


CASES = {
    "container_list": (
        {"containers": []},
        ["runtime_inventory", "runtime_status"],
        "runtime_inventory",
    ),
    "container_logs": (
        {
            "container_id": "c1",
            "logs": "ready",
            "truncated": False,
            "tail": 20,
            "since": "",
            "limit_chars": 16000,
        },
        ["runtime_logs"],
        "runtime_logs",
    ),
}


def _schema(tool_name):
    return next(tool["outputSchema"] for tool in bundle_dispatch.TOOLS if tool["name"] == tool_name)


def _plan(tool_name, evidence_type):
    step = PlanStep(
        step_id="s1",
        title="Inspect runtime",
        goal="Return verified runtime data",
        tool=tool_name,
        tool_arguments={},
        required_evidence=[evidence_type],
    )
    return ThinkingPlan(
        intent="inspect runtime",
        steps=[step],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="r7-p2",
    ), step


def test_container_results_validate_and_complete_with_manifest_evidence(monkeypatch):
    for tool_name, (payload, evidence_types, required_evidence) in CASES.items():
        monkeypatch.setattr(bundle_dispatch, "_find_tool", lambda _name, result=payload: lambda: result)
        response = bundle_dispatch.handle_request(
            {
                "jsonrpc": "2.0",
                "id": "r7-p2",
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": {}},
            }
        )
        envelope = project_tool_result_envelope(
            MCPTransportRequestOutcome(MCPTransportRequestStatus.OK, payload=response["result"])
        )
        structural = validate_structured_output(_schema(tool_name), envelope)

        assert response["result"] == {
            "content": [],
            "structuredContent": payload,
            "isError": False,
        }
        assert structural.status is MCPStructuralValidationStatus.VALID
        artifacts = validated_evidence_artifacts(
            tool_name=tool_name,
            step_id="s1",
            output=payload,
            tool_detail={"capability_evidence_types": evidence_types},
            structural_result=structural,
            structural_validation_status=TaskStructuralValidationStatus.VALID,
            operation_contract_fingerprint="fp-r7-p2",
        )
        plan, _step = _plan(tool_name, required_evidence)
        decision = evaluate(
            plan,
            [EvidenceArtifact.from_dict(item) for item in artifacts],
            expected_operation_contract_fingerprint="fp-r7-p2",
        )
        assert decision.action is OutcomeAction.COMPLETE


def test_typed_tool_failure_sets_is_error_without_text_heuristics(monkeypatch):
    payload = {
        "ok": False,
        "error": {"code": "RUNTIME_UNAVAILABLE", "message": "offline", "retryable": True},
    }
    monkeypatch.setattr(bundle_dispatch, "_find_tool", lambda _name: lambda: payload)

    response = bundle_dispatch.handle_request(
        {
            "jsonrpc": "2.0",
            "id": "r7-p2-error",
            "method": "tools/call",
            "params": {"name": "container_list", "arguments": {}},
        }
    )

    assert response["result"]["structuredContent"] == payload
    assert response["result"]["isError"] is True
