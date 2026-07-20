from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


def _plan(*steps: PlanStep) -> ThinkingPlan:
    return ThinkingPlan(
        intent="run_tools",
        steps=list(steps),
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        context_hints={"user_text": "Original objective from context"},
        plan_id="plan-1",
    )


def _step(step_id: str, tool: str | None = "demo_tool") -> PlanStep:
    return PlanStep(
        step_id=step_id,
        title=f"Step {step_id}",
        goal=f"Goal {step_id}",
        tool=tool,
        tool_arguments={"step": step_id} if tool else {},
    )


def _risky_step(step_id: str) -> PlanStep:
    return PlanStep(
        step_id=step_id,
        title=f"Step {step_id}",
        goal=f"Goal {step_id}",
        tool="demo_tool",
        tool_arguments={"step": step_id},
        risk=RiskLevel.NEEDS_CONFIRMATION,
    )
