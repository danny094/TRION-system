from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus
from core.task_loop.step_operation_receipt import StepOperationReceipt


def blocked_execution_result(
    step_id: str,
    tool_name: str,
    error: str,
    event_sink,
    *,
    status: StepExecutionStatus = StepExecutionStatus.FAILED,
    receipt: StepOperationReceipt | None = None,
) -> StepExecutionResult:
    _emit(
        event_sink,
        {
            "type": "tool_result",
            "status": status.value,
            "success": False,
            "artifact_count": 0,
        },
    )
    return StepExecutionResult(step_id=step_id, status=status, error=error, receipt=receipt)


def _emit(event_sink, payload: dict) -> None:
    if not callable(event_sink):
        return
    try:
        event_sink(dict(payload))
    except Exception:
        return
