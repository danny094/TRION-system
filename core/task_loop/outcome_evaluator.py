"""
core.task_loop.outcome_evaluator
=================================
Deterministischer Evaluator: prüft, ob ein ThinkingPlan sein Ziel erreicht hat.

Eingabe : ThinkingPlan, List[EvidenceArtifact], available_evidence_types
Ausgabe : OutcomeDecision — complete | replan | block

Kein LLM-Call. Max 200 Zeilen (Doc 07).
Führende Doc: core/task_loop/README.md
Plan/ADR:    docs/implementation-plans/completed/51-taskloop-objective-completion.md (Phase 3)
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from core.task_loop.contracts import EvidenceArtifact, StopReason
from core.thinking.contracts import (
    INVALID_OPERATION_CONTRACT_CRITERION,
    PlanStep,
    ThinkingPlan,
)


class OutcomeAction(str, Enum):
    """Ausgabe von outcome_evaluator: hat der Loop sein Ziel erreicht?"""

    COMPLETE = "complete"
    REPLAN = "replan"
    BLOCK = "block"


@dataclass(frozen=True)
class OutcomeDecision:
    """Entscheidung des outcome_evaluator nach Prüfung aller PlanStep-Kriterien."""

    action: OutcomeAction
    stop_reason: Optional[StopReason] = None


def evaluate(
    plan: ThinkingPlan,
    artifacts: List[EvidenceArtifact],
    *,
    available_evidence_types: frozenset = frozenset(),
    replan_budget_remaining: bool = True,
    expected_operation_contract_fingerprint: str | None = None,
) -> OutcomeDecision:
    """Prüft alle PlanSteps mit Completion-Kriterien gegen gesammelte Artifacts.

    Steps ohne done_when/required_evidence werden übersprungen (Backward-Compat:
    step-SUCCESS = fertig, kein explizites Ziel-Kriterium).
    """
    for step in plan.steps:
        decision = _evaluate_step(
            step,
            artifacts,
            available_evidence_types=available_evidence_types,
            replan_budget_remaining=replan_budget_remaining,
            expected_operation_contract_fingerprint=expected_operation_contract_fingerprint,
        )
        if decision.action != OutcomeAction.COMPLETE:
            return decision
    return OutcomeDecision(action=OutcomeAction.COMPLETE)


def _evaluate_step(
    step: PlanStep,
    artifacts: List[EvidenceArtifact],
    *,
    available_evidence_types: frozenset,
    replan_budget_remaining: bool,
    expected_operation_contract_fingerprint: str | None,
) -> OutcomeDecision:
    if step.done_when == INVALID_OPERATION_CONTRACT_CRITERION:
        return OutcomeDecision(
            action=OutcomeAction.BLOCK,
            stop_reason=StopReason.OBJECTIVE_NOT_MET,
        )
    # Kein Kriterium gesetzt → heutiges Verhalten (step-SUCCESS = fertig)
    if not step.done_when and not step.required_evidence:
        return OutcomeDecision(action=OutcomeAction.COMPLETE)

    step_artifacts = [a for a in artifacts if a.step_id == step.step_id]

    # required_evidence prüfen
    if step.required_evidence:
        collected_types = {
            a.artifact_type
            for a in step_artifacts
            if _counts_for_required_evidence(a, expected_operation_contract_fingerprint)
        }
        missing = [t for t in step.required_evidence if t not in collected_types]
        if missing:
            # Kein registriertes Tool kann den Typ erzeugen → CAPABILITY_GAP
            if available_evidence_types and not any(
                t in available_evidence_types for t in missing
            ):
                return OutcomeDecision(
                    action=OutcomeAction.BLOCK,
                    stop_reason=StopReason.CAPABILITY_GAP,
                )
            if replan_budget_remaining:
                return OutcomeDecision(
                    action=OutcomeAction.REPLAN,
                    stop_reason=StopReason.OBJECTIVE_NOT_MET,
                )
            return OutcomeDecision(
                action=OutcomeAction.BLOCK,
                stop_reason=StopReason.OBJECTIVE_NOT_MET,
            )

    # done_when prüfen
    if step.done_when and not _check_done_when(step.done_when, step_artifacts):
        if replan_budget_remaining:
            return OutcomeDecision(
                action=OutcomeAction.REPLAN,
                stop_reason=StopReason.OBJECTIVE_NOT_MET,
            )
        return OutcomeDecision(
            action=OutcomeAction.BLOCK,
            stop_reason=StopReason.OBJECTIVE_NOT_MET,
        )

    return OutcomeDecision(action=OutcomeAction.COMPLETE)


def _check_done_when(done_when: str, step_artifacts: List[EvidenceArtifact]) -> bool:
    """Wertet ein done_when-Kriterium gegen Step-Artifacts aus.

    Unterstützte Formate:
    - "file_created"              → artifact_type == "file_content" vorhanden
    - "exit_code:0"               → metadata.exit_code == "0"
    - "stdout_contains:PASSED"    → content enthält Substring
    - "artifact_type:file_content"→ artifact_type == Wert vorhanden
    Unbekannte nicht-leere Formate → False (fail-closed).
    """
    if done_when == "file_created":
        return any(a.artifact_type == "file_content" for a in step_artifacts)

    if done_when.startswith("exit_code:"):
        expected = done_when.split(":", 1)[1]
        return any(
            str(a.metadata.get("exit_code", "")) == expected for a in step_artifacts
        )

    if done_when.startswith("stdout_contains:"):
        substring = done_when.split(":", 1)[1]
        return any(substring in a.content for a in step_artifacts)

    if done_when.startswith("artifact_type:"):
        required_type = done_when.split(":", 1)[1]
        return any(a.artifact_type == required_type for a in step_artifacts)

    return False


def _counts_for_required_evidence(
    artifact: EvidenceArtifact,
    expected_operation_contract_fingerprint: str | None,
) -> bool:
    expected = str(expected_operation_contract_fingerprint or "").strip()
    if not expected:
        return False
    return (
        artifact.metadata.get("validated_evidence") is True
        and str(artifact.metadata.get("operation_contract_fingerprint") or "").strip() == expected
    )
