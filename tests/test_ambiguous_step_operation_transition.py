from core.orchestrator.contracts import ToolDescriptor
from core.pipeline.plan_contract_validator import (
    authorized_contract_for_receipt,
    issue_followup_step_receipt,
    issue_initial_step_receipt,
)
from core.pipeline.task_loop_stage import build_task_loop_stage
from core.orchestrator.tool_eligibility import eligible_tools_for_contract
from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus, TaskLoopState
from core.task_loop.executor import TaskToolResult
from core.task_loop.step_operation_receipt import StepOperationReceipt
from core.task_loop.task_loop import start_task_loop
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.operation_contract_context import canonical_contract_context


def _context():
    return canonical_contract_context(allowed_transitions=("list->logs", "list->inspect"))


def _tool(name, operation):
    return ToolDescriptor(
        name=name, capability_domain="container_runtime",
        capability_operation=operation, capability_evidence_types=[],
        capability_target_scopes=["runtime_state"], capability_risk="read_only",
    )


def test_ambiguous_followup_transition_blocks_receipt_eligibility_and_toolstart():
    context = _context()
    initial = issue_initial_step_receipt("list-step", context=context)
    predecessor = StepExecutionResult("list-step", StepExecutionStatus.SUCCESS, receipt=initial)
    assert issue_followup_step_receipt("logs-step", predecessor, context=context) is None
    fingerprint = context["routing_frame"]["operation_contract_fingerprint"]
    forged = StepOperationReceipt("logs-step", "logs", fingerprint, True)
    unauthorized = authorized_contract_for_receipt(forged, context=context, predecessor=predecessor)
    assert unauthorized == {}
    assert eligible_tools_for_contract(
        [_tool("inventory", "list"), _tool("log_reader", "logs")], unauthorized
    ) == []

    plan = ThinkingPlan(
        intent="run", needs_task_loop=True, risk_level=RiskLevel.SAFE, plan_id="ambiguous",
        steps=[
            PlanStep(step_id="list-step", title="List", goal="List", tool="inventory"),
            PlanStep(step_id="logs-step", title="Logs", goal="Logs", tool="log_reader"),
        ],
    )
    calls = []
    result = build_task_loop_stage(
        plan, conversation_id="conv", objective="objective", task_loop_fn=start_task_loop,
        tool_runner=lambda call: calls.append(call.tool_name) or TaskToolResult(success=True, result={}),
        replanner_fn=lambda *_args, **_kwargs: None, max_steps=4,
        max_retries_per_step=0, max_replans=0,
        available_tools=[_tool("inventory", "list"), _tool("log_reader", "logs")],
        orchestrator_context=context,
    ).result

    assert calls == ["inventory"]
    assert result.state is TaskLoopState.BLOCKED
