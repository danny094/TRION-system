from copy import deepcopy
from dataclasses import replace

from core.orchestrator.contracts import ToolDescriptor
from core.pipeline.operation_contract_context import ReceiptConfigurationState, receipt_configuration_state
from core.pipeline.plan_contract_validator import issue_initial_step_receipt
from core.pipeline.task_loop_stage import build_step_receipt_issuer, build_step_receipt_validator, build_task_loop_stage
from core.task_loop.contracts import StepOperationExecution, StepExecutionStatus, TaskLoopSnapshot, TaskLoopState
from core.task_loop.executor import TaskToolResult
from core.task_loop.runner import run_task_loop
from core.task_loop.task_loop import start_task_loop
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.operation_contract_context import canonical_contract_context


def _context(*, contract=True, fingerprint="fp"):
    if contract is True:
        context = canonical_contract_context()
        if fingerprint is None:
            context["routing_frame"].pop("operation_contract_fingerprint")
        elif fingerprint != "fp":
            context["routing_frame"]["operation_contract_fingerprint"] = fingerprint
        return context
    frame = {}
    if contract is not False:
        frame["operation_contract"] = contract
    if fingerprint is not None:
        frame["operation_contract_fingerprint"] = fingerprint
    return {"routing_frame": frame} if frame else {}


def _plan(tool="inventory"):
    return ThinkingPlan(
        intent="run", steps=[PlanStep("list-step", "List", "List", tool=tool)],
        needs_task_loop=True, risk_level=RiskLevel.SAFE, plan_id="plan",
    )


def _tool(name="inventory", operation="list"):
    return ToolDescriptor(
        name=name, capability_domain="container_runtime", capability_operation=operation,
        capability_evidence_types=[], capability_target_scopes=["runtime_state"],
        capability_risk="read_only",
    )


def test_receipt_configuration_matrix_is_explicit_and_fail_closed():
    assert receipt_configuration_state({}) is ReceiptConfigurationState.LEGACY_VALID
    assert receipt_configuration_state(_context()) is ReceiptConfigurationState.RECEIPT_MODE_ACTIVE
    inconsistent = [
        _context(fingerprint=None), _context(contract=False), _context(contract={}),
        _context(fingerprint=7),
    ]
    assert all(receipt_configuration_state(item) is ReceiptConfigurationState.INCONSISTENT_FAIL_CLOSED for item in inconsistent)
    assert receipt_configuration_state({}, receipt_provenance=True) is ReceiptConfigurationState.INCONSISTENT_FAIL_CLOSED
    assert receipt_configuration_state({}, receipt_callbacks=True) is ReceiptConfigurationState.INCONSISTENT_FAIL_CLOSED
    assert receipt_configuration_state({}) is ReceiptConfigurationState.LEGACY_VALID
    assert receipt_configuration_state(
        _context(), receipt_history_present=False,
    ) is ReceiptConfigurationState.INCONSISTENT_FAIL_CLOSED


def test_contract_mutations_do_not_reuse_stale_canonical_fingerprint():
    mutations = (
        lambda contract: contract.__setitem__("domain", ""),
        lambda contract: contract.__setitem__("allowed_operations", "list"),
        lambda contract: contract.__setitem__("allowed_transitions", ["list->inspect"]),
        lambda contract: contract.__setitem__("required_evidence", ["runtime_metadata"]),
        lambda contract: contract.__setitem__("target", "changed-target"),
        lambda contract: contract.__setitem__("scope_lock", "changed-scope"),
    )
    for mutate in mutations:
        context = deepcopy(_context())
        mutate(context["routing_frame"]["operation_contract"])
        assert receipt_configuration_state(context) is ReceiptConfigurationState.INCONSISTENT_FAIL_CLOSED


def test_foreign_fingerprint_and_primary_not_allowed_fail_closed():
    assert receipt_configuration_state(_context(fingerprint="foreign-fingerprint")) is ReceiptConfigurationState.INCONSISTENT_FAIL_CLOSED
    context = deepcopy(_context())
    context["routing_frame"]["operation_contract"]["primary_operation"] = "inspect"
    assert receipt_configuration_state(context) is ReceiptConfigurationState.INCONSISTENT_FAIL_CLOSED


def test_transport_receipt_without_validator_blocks_before_tool_start():
    receipt = issue_initial_step_receipt("list-step", context=_context())
    calls = []
    result = run_task_loop(
        _plan(), TaskLoopSnapshot("plan", "conv", "run", TaskLoopState.EXECUTING, 0, 2, 0),
        lambda call: calls.append(call) or TaskToolResult(True, {}),
        step_receipts={"list-step": receipt}, receipt_mode=True,
    )
    assert result.state is TaskLoopState.BLOCKED
    assert calls == []


def test_validator_foreign_return_types_block_before_tool_start():
    for value in (False, True, {}, "RECEIPT_SENTINEL", object()):
        calls = []
        events = []
        result = run_task_loop(
            _plan(), TaskLoopSnapshot("plan", "conv", "run", TaskLoopState.EXECUTING, 0, 2, 0),
            lambda call: calls.append(call) or TaskToolResult(True, {}),
            receipt_issuer=build_step_receipt_issuer(_context()),
            receipt_validator=lambda *_args, result=value: result, receipt_mode=True,
            event_sink=lambda event: events.append(dict(event)),
        )
        assert result.state is TaskLoopState.BLOCKED
        assert calls == []
        assert result.snapshot.step_operation_executions == []
        assert all(event.get("type") != "tool_start" for event in events)


def test_new_issuer_receipt_also_requires_validator_acceptance():
    calls = []
    result = run_task_loop(
        _plan(), TaskLoopSnapshot("plan", "conv", "run", TaskLoopState.EXECUTING, 0, 2, 0),
        lambda call: calls.append(call) or TaskToolResult(True, {}),
        receipt_issuer=build_step_receipt_issuer(_context()),
        receipt_validator=lambda *_args: None, receipt_mode=True,
    )
    assert result.state is TaskLoopState.BLOCKED
    assert calls == []


def test_validator_exception_blocks_before_tool_start():
    calls = []

    def broken_validator(*_args):
        raise RuntimeError("internal validator detail")

    result = run_task_loop(
        _plan(), TaskLoopSnapshot("plan", "conv", "run", TaskLoopState.EXECUTING, 0, 2, 0),
        lambda call: calls.append(call) or TaskToolResult(True, {}),
        receipt_issuer=build_step_receipt_issuer(_context()),
        receipt_validator=broken_validator, receipt_mode=True,
    )
    assert result.state is TaskLoopState.BLOCKED
    assert calls == []


def test_execution_provenance_without_contract_is_inconsistent():
    receipt = issue_initial_step_receipt("list-step", context=_context())
    execution = StepOperationExecution(receipt, StepExecutionStatus.SUCCESS)
    assert receipt_configuration_state({}, receipt_provenance=bool([execution])) is ReceiptConfigurationState.INCONSISTENT_FAIL_CLOSED


def test_inconsistent_pipeline_configuration_blocks_before_tool_start():
    calls = []
    result = build_task_loop_stage(
        _plan(), conversation_id="conv", objective="run", task_loop_fn=start_task_loop,
        tool_runner=lambda call: calls.append(call) or TaskToolResult(True, {}),
        replanner_fn=None, max_steps=2, max_retries_per_step=0, max_replans=0,
        available_tools=[_tool()], receipt_tool_descriptors=[_tool()],
        orchestrator_context=_context(contract=False),
    ).result
    assert result.state is TaskLoopState.BLOCKED
    assert calls == []


def test_stale_contract_fingerprint_blocks_pipeline_before_tool_start():
    calls = []
    events = []
    result = build_task_loop_stage(
        _plan(), conversation_id="conv", objective="run", task_loop_fn=start_task_loop,
        tool_runner=lambda call: calls.append(call) or TaskToolResult(True, {}),
        replanner_fn=None, max_steps=2, max_retries_per_step=0, max_replans=0,
        available_tools=[_tool()], receipt_tool_descriptors=[_tool()],
        orchestrator_context=_context(fingerprint="stale-fingerprint"),
        event_sink=lambda event: events.append(dict(event)),
    ).result
    assert result.state is TaskLoopState.BLOCKED
    assert calls == []
    assert all(event.get("type") != "tool_start" for event in events)
