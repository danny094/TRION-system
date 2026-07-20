from dataclasses import replace

from core.pipeline.plan_contract_validator import issue_initial_step_receipt
from core.pipeline.task_loop_stage import build_step_receipt_validator
from core.task_loop.contracts import StepExecutionStatus, StepOperationExecution
from core.task_loop.step_operation_receipt import ReceiptValidationContext, StepOperationReceipt
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.test_receipt_trust_configuration import _context, _plan, _tool


def _provenance(plan, index, completed=(), executions=()):
    return ReceiptValidationContext(
        tuple(step.step_id for step in plan.steps), index, tuple(completed),
        tuple(executions), plan.steps[index].step_id,
    )


def test_initial_receipt_step_and_tool_mismatches_fail_closed():
    context, plan = _context(), _plan(tool="log_reader")
    receipt = issue_initial_step_receipt("list-step", context=context)
    validator = build_step_receipt_validator(context, [_tool(), _tool("log_reader", "logs")], plan)
    provenance = _provenance(plan, 0)
    assert validator(plan.steps[0], replace(receipt, step_id="other-step"), provenance) is None
    assert validator(plan.steps[0], receipt, provenance) is None


def test_later_primary_receipt_cannot_restart_initial_authorization():
    context = _context()
    plan = ThinkingPlan(
        "run", [PlanStep("list-step", "List", "List", tool="inventory"),
                PlanStep("second-step", "List again", "List", tool="inventory")],
        True, RiskLevel.SAFE, plan_id="plan",
    )
    first = issue_initial_step_receipt("list-step", context=context)
    executions = [StepOperationExecution(first, StepExecutionStatus.SUCCESS)]
    validator = build_step_receipt_validator(context, [_tool()], plan)
    provenance = _provenance(plan, 1, ["list-step"], executions)
    assert validator(plan.steps[1], replace(first, step_id="second-step"), provenance) is None


def test_foreign_validator_result_collections_and_subclass_block():
    class ReceiptSubclass(StepOperationReceipt):
        pass

    values = ([], {"receipt": "sentinel"}, ReceiptSubclass("list-step", "list", "fp", True))
    from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopState
    from core.task_loop.executor import TaskToolResult
    from core.task_loop.runner import run_task_loop
    for value in values:
        calls = []
        result = run_task_loop(
            _plan(), TaskLoopSnapshot("plan", "conv", "run", TaskLoopState.EXECUTING, 0, 2, 0),
            lambda call: calls.append(call) or TaskToolResult(True, {}),
            receipt_issuer=lambda *_args: issue_initial_step_receipt("list-step", context=_context()),
            receipt_validator=lambda *_args, result=value: result, receipt_mode=True,
        )
        assert result.state is TaskLoopState.BLOCKED
        assert result.snapshot.step_operation_executions == []
        assert calls == []
