from typing import Any, Mapping

from core.task_loop.document_resolution import collect_result_artifacts, resolve_tool_arguments
from core.task_loop.evidence_adapter import validated_evidence_artifacts
from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus
from core.task_loop.execution_block import blocked_execution_result
from core.task_loop.step_operation_receipt import StepOperationReceipt
from core.task_loop.executable_now import check_executable_now
from core.task_loop.tool_execution_contracts import (
    _TASK_TOOL_RESULT_MISSING,
    TaskLoopEventSink,
    TaskStructuralValidationStatus,
    TaskToolCall,
    TaskToolResult,
    TaskToolResultStatus,
    ToolRunner,
)
from core.task_loop.toolcall_governor import toolcall_governor_error
from core.thinking.contracts import PlanStep


def _timeout_for_step(step: PlanStep, default_timeout_s: float) -> float:
    raw = step.timeout_s if step.timeout_s is not None else default_timeout_s
    return max(0.2, float(raw or 0.0))


def build_tool_call(
    step: PlanStep,
    artifacts: list[dict[str, Any]] | None = None,
    default_timeout_s: float = 30.0,
    output_schema: Mapping[str, Any] | None = None,
) -> TaskToolCall:
    return TaskToolCall(
        tool_name=str(step.tool or "").strip(),
        arguments=resolve_tool_arguments(dict(step.tool_arguments or {}), artifacts or []),
        step_id=step.step_id,
        timeout_s=_timeout_for_step(step, default_timeout_s),
        output_schema=output_schema,
    )


def execute_step(
    step: PlanStep,
    tool_runner: ToolRunner,
    *,
    artifacts: list[dict[str, Any]] | None = None,
    default_timeout_s: float = 30.0,
    event_sink: TaskLoopEventSink | None = None,
    tool_details_by_name: Mapping[str, Mapping[str, Any]] | None = None,
    operation_contract_fingerprint: str | None = None,
    governor_snapshot: object | None = None,
    receipt: StepOperationReceipt | None = None,
) -> StepExecutionResult:
    if not step.tool:
        return blocked_execution_result(
            step.step_id, "", "missing_tool", event_sink, status=StepExecutionStatus.SKIPPED, receipt=receipt
        )

    detail = (tool_details_by_name or {}).get(str(step.tool or "").strip())
    output_schema = None
    if isinstance(detail, Mapping) and detail.get("capability_output_schema") == "mcp_output_schema":
        candidate = detail.get("output_schema")
        if isinstance(candidate, Mapping):
            output_schema = candidate
    tool_call = build_tool_call(
        step,
        artifacts=artifacts,
        default_timeout_s=default_timeout_s,
        output_schema=output_schema,
    )
    executable = check_executable_now(tool_call, tool_details_by_name)
    if not executable.allowed:
        error = executable.error or "not_executable_now"
        return blocked_execution_result(step.step_id, tool_call.tool_name, error, event_sink, receipt=receipt)
    governor_error = toolcall_governor_error(governor_snapshot)
    if governor_error:
        return blocked_execution_result(step.step_id, tool_call.tool_name, governor_error, event_sink, receipt=receipt)
    _tool_start_payload = {
        "type": "tool_start",
        "timeout_s": tool_call.timeout_s,
    }
    _emit(event_sink, _tool_start_payload)
    _emit_progress(event_sink, _tool_start_payload, step_title=step.title)
    try:
        tool_result = tool_runner(tool_call)
    except Exception as exc:
        _exc_result_payload = {
            "type": "tool_result",
            "status": StepExecutionStatus.FAILED.value,
            "success": False,
            "artifact_count": 0,
        }
        _emit(event_sink, _exc_result_payload)
        _emit_progress(event_sink, _exc_result_payload, step_title=step.title)
        return StepExecutionResult(
            step_id=step.step_id,
            status=StepExecutionStatus.FAILED,
            error=str(exc),
            tool_call_started=True,
            receipt=receipt,
        )

    if not tool_result.success:
        error = str(tool_result.error or "")
        status = StepExecutionStatus.TIMEOUT if error.startswith("mcp_timeout:") else StepExecutionStatus.FAILED
        _fail_result_payload = {
            "type": "tool_result",
            "status": status.value,
            "success": False,
            "artifact_count": 0,
        }
        _emit(event_sink, _fail_result_payload)
        _emit_progress(event_sink, _fail_result_payload, step_title=step.title)
        return StepExecutionResult(
            step_id=step.step_id,
            status=status,
            output=dict(tool_result.result or {}),
            error=error or "tool_failed",
            tool_call_started=True,
            receipt=receipt,
        )

    output = dict(tool_result.result or {})
    base_artifacts = output.get("artifacts") if isinstance(output.get("artifacts"), list) else []
    evidence = validated_evidence_artifacts(
        tool_name=tool_call.tool_name,
        step_id=step.step_id,
        output=output,
        tool_detail=(tool_details_by_name or {}).get(tool_call.tool_name),
        structural_result=tool_result.structural_result,
        structural_validation_status=tool_result.structural_validation_status,
        operation_contract_fingerprint=operation_contract_fingerprint,
    )
    collected = collect_result_artifacts(step.tool, step.step_id, output, [*base_artifacts, *evidence])
    _ok_result_payload = {
        "type": "tool_result",
        "status": StepExecutionStatus.SUCCESS.value,
        "success": True,
        "artifact_count": len(collected),
    }
    _emit(event_sink, _ok_result_payload)
    _emit_progress(event_sink, _ok_result_payload, step_title=step.title)
    return StepExecutionResult(
        step_id=step.step_id,
        status=StepExecutionStatus.SUCCESS,
        output=output,
        artifacts=collected,
        tool_call_started=True,
        receipt=receipt,
        structural_result=tool_result.structural_result,
    )


def _emit(event_sink: TaskLoopEventSink | None, payload: dict[str, Any]) -> None:
    if not callable(event_sink):
        return
    try:
        event_sink(dict(payload))
    except Exception:
        return


def _emit_progress(
    event_sink: TaskLoopEventSink | None,
    raw_event: dict[str, Any],
    step_title: str = "",
) -> None:
    if not callable(event_sink):
        return
    from core.task_loop.progress_utterance_builder import build_progress_utterance
    payload = build_progress_utterance({**raw_event, "step_title": step_title})
    if payload is not None:
        _emit(event_sink, payload)
