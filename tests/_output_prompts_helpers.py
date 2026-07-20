from core.thinking.contracts import RiskLevel, ThinkingPlan


def plan_answer_user() -> ThinkingPlan:
    return ThinkingPlan(
        intent="answer_user",
        steps=[],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
        reasoning="test",
    )
