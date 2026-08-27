"""Bind receipt-authorized composite follow-ups to the Thinking owner."""
from typing import Any

from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_eligibility import eligible_tools_for_contract
from core.pipeline.operation_contract_context import operation_contract_from_context
from core.pipeline.output_evidence_contracts import OutputEvidenceItem
from core.pipeline.plan_contract_validator import (
    authorized_contract_for_receipt,
    issue_followup_step_receipt,
)
from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus
from core.thinking.composite_followup import (
    ValidatedFollowupEvidence,
    bind_followup_target,
    followup_step_id,
    plan_authorized_followup,
)


def build_composite_followup_planner(context: Any, descriptors: Any, projector: Any):
    tools = tuple(tool for tool in list(descriptors or ()) if type(tool) is ToolDescriptor)
    if not tools or not callable(projector):
        return None

    def plan_followup(plan, predecessor_step, result):
        if type(result) is not StepExecutionResult or result.status is not StepExecutionStatus.SUCCESS:
            return None
        try:
            projected = projector(result.structural_result)
        except Exception:
            return None
        if type(projected) is not OutputEvidenceItem:
            return None
        evidence = ValidatedFollowupEvidence(projected.structured_content)
        target = bind_followup_target(evidence, operation_contract_from_context(context))
        if target is None:
            return None
        step_id = followup_step_id(getattr(predecessor_step, "step_id", ""))
        receipt = issue_followup_step_receipt(step_id, result, context=context)
        contract = authorized_contract_for_receipt(receipt, context=context, predecessor=result)
        eligible = eligible_tools_for_contract(list(tools), contract)
        if len(eligible) != 1:
            return None
        required_evidence = tuple(contract.get("required_evidence", ()))
        if (
            not required_evidence
            or any(type(item) is not str or not item or item != item.strip() for item in required_evidence)
        ):
            return None
        return plan_authorized_followup(
            plan, getattr(predecessor_step, "step_id", ""), eligible[0], target, required_evidence,
        )

    return plan_followup
