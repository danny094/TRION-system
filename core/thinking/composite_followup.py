"""Typed planning for an already authorized composite follow-up."""
from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any

from core.orchestrator.contracts import ToolDescriptor
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


@dataclass(frozen=True)
class ValidatedFollowupEvidence:
    structured_content: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.structured_content, Mapping):
            raise TypeError("structured_content must be a mapping")
        object.__setattr__(self, "structured_content", _freeze(self.structured_content))


@dataclass(frozen=True)
class BoundFollowupTarget:
    container_id: str

    def __post_init__(self) -> None:
        value = _clean(self.container_id)
        if not value:
            raise ValueError("container_id must be non-empty")
        object.__setattr__(self, "container_id", value)


def followup_step_id(predecessor_step_id: str) -> str:
    predecessor = str(predecessor_step_id or "").strip()
    return f"{predecessor}-followup" if predecessor else ""


def bind_followup_target(
    evidence: ValidatedFollowupEvidence,
    operation_contract: Mapping[str, Any],
) -> BoundFollowupTarget | None:
    if type(evidence) is not ValidatedFollowupEvidence or not isinstance(operation_contract, Mapping):
        return None
    candidates = _container_candidates(evidence.structured_content)
    selected = _select_candidate(candidates, _contract_target(operation_contract))
    return BoundFollowupTarget(selected[0]) if selected is not None else None


def plan_authorized_followup(
    plan: ThinkingPlan,
    predecessor_step_id: str,
    successor_tool: ToolDescriptor,
    target: BoundFollowupTarget,
    required_evidence: tuple[str, ...],
) -> ThinkingPlan | None:
    if (
        type(plan) is not ThinkingPlan
        or type(successor_tool) is not ToolDescriptor
        or type(target) is not BoundFollowupTarget
        or type(required_evidence) is not tuple
        or not required_evidence
        or any(type(item) is not str or not item or item != item.strip() for item in required_evidence)
    ):
        return None
    step_id = followup_step_id(predecessor_step_id)
    if not step_id or any(step.step_id == step_id for step in plan.steps):
        return None
    followup = PlanStep(
        step_id=step_id,
        title=f"Run {successor_tool.capability_operation}",
        goal=f"Collect {successor_tool.capability_operation} evidence for the bound target",
        tool=successor_tool.name,
        tool_arguments={"container_id": target.container_id},
        risk=RiskLevel.SAFE,
        required_evidence=list(required_evidence),
    )
    return replace(plan, steps=[*plan.steps, followup])


def _container_candidates(content: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    values = content.get("containers")
    if not isinstance(values, (list, tuple)):
        return ()
    candidates = []
    for value in values:
        if not isinstance(value, Mapping):
            return ()
        container_id = _clean(value.get("container_id"))
        name = _clean(value.get("name"))
        if not container_id or not name:
            return ()
        candidates.append((container_id, name))
    identifiers = [item[0] for item in candidates]
    return tuple(candidates) if len(set(identifiers)) == len(identifiers) else ()


def _contract_target(contract: Mapping[str, Any]) -> str | None:
    values = contract.get("targets")
    if not isinstance(values, (list, tuple)):
        return None
    targets = tuple(_clean(value) for value in values)
    projected = _clean(contract.get("target"))
    if not targets:
        return "" if not projected else None
    if len(targets) != 1 or not targets[0] or projected != targets[0]:
        return None
    return projected


def _select_candidate(candidates: tuple[tuple[str, str], ...], target: str | None) -> tuple[str, str] | None:
    if target is None:
        return None
    if target:
        matches = tuple(item for item in candidates if target in item)
        return matches[0] if len(matches) == 1 else None
    return candidates[0] if len(candidates) == 1 else None


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("structured_content must be JSON-compatible")


def _clean(value: Any) -> str:
    return value.strip() if type(value) is str else ""
