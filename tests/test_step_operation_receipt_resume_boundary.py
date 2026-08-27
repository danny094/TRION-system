from dataclasses import replace

import pytest

from core.pipeline.common import public_task_artifacts, public_task_loop_snapshot
from core.pipeline.plan_contract_validator import authorized_contract_for_receipt, issue_initial_step_receipt, issue_followup_step_receipt
from core.pipeline.task_loop_stage import build_step_receipt_issuer
from core.routing_frame.contracts import OperationTransition
from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus, StepOperationExecution, TaskLoopSnapshot, TaskLoopState
from core.task_loop.step_operation_receipt import StepOperationReceipt
from core.thinking.contracts import PlanStep
from adapters.task_resume_serialization import snapshot_from_dict, snapshot_to_dict
from adapters.task_resume_receipts import step_operation_executions
from tests.operation_contract_context import canonical_contract_context


def _context():
    return canonical_contract_context(
        target="TARGET_SENTINEL",
        scope_lock="SCOPE_SENTINEL",
        transition_requirements=(OperationTransition("list", "logs", ("runtime_logs",)),),
    )


def _snapshot():
    receipt = issue_initial_step_receipt("list-step", context=_context())
    return TaskLoopSnapshot("PLAN_ID_SENTINEL", "CONVERSATION_ID_SENTINEL", "USER_TEXT_SENTINEL", TaskLoopState.WAITING, 1, 4, 0,
                            step_operation_executions=[StepOperationExecution(receipt, StepExecutionStatus.SUCCESS)])


def test_resume_serialization_preserves_internal_receipt_execution():
    restored = snapshot_from_dict(snapshot_to_dict(_snapshot()))
    assert restored.step_operation_executions == _snapshot().step_operation_executions


def test_public_snapshot_projection_removes_all_receipt_fields_and_sentinels():
    snapshot = replace(
        _snapshot(), waiting_reason="plan_contract_unknown_tool:TOOL_SENTINEL",
        waiting_source="WAITING_SOURCE_SENTINEL",
    )
    public = public_task_loop_snapshot(snapshot)
    serialized = repr(public)
    forbidden = {
        "objective", "plan_id", "conversation_id", "completed_steps", "pending_step",
        "retry_counts", "progress_signature", "step_operation_executions",
        "waiting_reason", "waiting_source",
    }
    assert forbidden.isdisjoint(public)
    for sentinel in (
        "USER_TEXT_SENTINEL", "PLAN_ID_SENTINEL", "CONVERSATION_ID_SENTINEL",
        "TARGET_SENTINEL", "SCOPE_SENTINEL", "FP_SENTINEL",
        "TOOL_SENTINEL", "WAITING_SOURCE_SENTINEL",
    ):
        assert sentinel not in serialized


def test_public_snapshot_artifacts_are_type_only():
    snapshot = _snapshot()
    snapshot = snapshot.__class__(**{**snapshot.__dict__, "artifacts": [{
        "artifact_type": "tool_result", "id": "ID_SENTINEL", "result": "OUTPUT_SENTINEL",
        "metadata": {"operation_contract_fingerprint": "FP_SENTINEL"},
    }]})
    public = public_task_loop_snapshot(snapshot)
    assert public["artifacts"] == [{"artifact_type": "tool_result"}]
    assert "ID_SENTINEL" not in repr(public)
    assert "OUTPUT_SENTINEL" not in repr(public)
    assert "FP_SENTINEL" not in repr(public)


def test_public_artifacts_do_not_echo_unknown_type_or_payload_sentinels():
    public = public_task_artifacts([{
        "artifact_type": "SECRET_SENTINEL", "id": "STEP_ID_SENTINEL",
        "target": "TARGET_SENTINEL", "scope": "SCOPE_SENTINEL",
        "arguments": "ARGUMENT_SENTINEL", "output": "OUTPUT_SENTINEL",
        "content": "CONTENT_SENTINEL", "operation_contract_fingerprint": "FP_SENTINEL",
    }])
    assert public == [{"artifact_type": "artifact"}]
    assert "SENTINEL" not in repr(public)


def test_receipt_chain_deserialization_is_atomic_for_any_malformed_position():
    valid = snapshot_to_dict(_snapshot())["step_operation_executions"][0]
    malformed_rows = [
        {"receipt": {"step_id": "incomplete"}, "status": "success"},
        {"receipt": {**valid["receipt"], "step_id": 7}, "status": "success"},
        {"receipt": {**valid["receipt"], "scope_preserved": "true"}, "status": "success"},
        {"receipt": valid["receipt"], "status": "unknown"},
    ]
    for malformed in malformed_rows:
        for rows in ([malformed, valid], [valid, malformed, valid], [valid, malformed]):
            with pytest.raises(ValueError):
                step_operation_executions(rows)


def test_old_snapshot_without_receipt_chain_remains_readable_and_empty():
    data = snapshot_to_dict(_snapshot())
    data.pop("step_operation_executions")
    assert snapshot_from_dict(data).step_operation_executions == []


def test_explicit_null_receipt_chain_is_not_legacy_missing_data():
    data = snapshot_to_dict(_snapshot())
    data["step_operation_executions"] = None
    with pytest.raises(ValueError):
        snapshot_from_dict(data)
    with pytest.raises(ValueError):
        step_operation_executions(None)


def test_forged_operation_and_logs_without_successful_predecessor_fail_closed():
    context = _context()
    forged = StepOperationReceipt("fake", "delete", "FP_SENTINEL", True)
    forged_logs = StepOperationReceipt("fake", "logs", "FP_SENTINEL", True)
    assert authorized_contract_for_receipt(forged, context=context) == {}
    assert authorized_contract_for_receipt(forged_logs, context=context) == {}

    initial = issue_initial_step_receipt("list-step", context=context)
    predecessor = StepExecutionResult("list-step", StepExecutionStatus.SUCCESS, receipt=initial)
    followup = issue_followup_step_receipt("logs-step", predecessor, context=context)
    assert authorized_contract_for_receipt(followup, context=context, predecessor=predecessor)["primary_operation"] == "logs"

    wrong_predecessor = replace(predecessor, receipt=replace(initial, operation_contract_fingerprint="OTHER_FP"))
    assert authorized_contract_for_receipt(followup, context=context, predecessor=wrong_predecessor) == {}


def test_issuer_output_is_untrusted_until_validator_checks_step_context():
    issuer = build_step_receipt_issuer(_context())
    step = PlanStep(step_id="logs-step", title="Logs", goal="Logs", tool="log_reader")
    receipt = issuer(step, None)
    assert receipt.operation == "list"
    assert receipt.step_id == step.step_id
