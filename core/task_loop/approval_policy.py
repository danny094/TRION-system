from core.task_loop.contracts import StopReason, TaskLoopSnapshot
from core.thinking.contracts import PlanStep, RiskLevel


def requires_waiting(step: PlanStep, snapshot: TaskLoopSnapshot) -> tuple[StopReason, str, str] | None:
    tool_name = str(step.tool or "").strip()
    if not tool_name:
        return None

    mode = str(snapshot.approval_mode or "risk_based").strip().lower()
    approval_required_tools = {str(name or "").strip() for name in snapshot.approval_required_tools if str(name or "").strip()}
    if tool_name in approval_required_tools:
        return (StopReason.RISK_GATE_REQUIRED, "approval_required", "tool_policy")
    if mode == "approval_first":
        return (StopReason.RISK_GATE_REQUIRED, "approval_required", "approval_mode")
    if mode == "risk_based" and step.risk == RiskLevel.NEEDS_CONFIRMATION:
        return (StopReason.RISK_GATE_REQUIRED, "risk_boundary", "approval_mode")
    return None
