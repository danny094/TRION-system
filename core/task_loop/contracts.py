from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from core.task_loop.step_operation_receipt import StepOperationReceipt


class TaskLoopState(str, Enum):
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    WAITING = "waiting"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class StopReason(str, Enum):
    MAX_STEPS_REACHED = "max_steps_reached"
    STEP_FAILED = "step_failed"
    ADDITIONAL_EVIDENCE_REQUIRED = "additional_evidence_required"
    REPLAN_BUDGET_EXHAUSTED = "replan_budget_exhausted"
    FAILURE_ABORT_POLICY = "failure_abort_policy"
    RISK_GATE_REQUIRED = "risk_gate_required"
    USER_DECISION_NEEDED = "user_decision_needed"
    NO_PROGRESS = "no_progress"
    USER_CANCELLED = "user_cancelled"
    OBJECTIVE_NOT_MET = "objective_not_met"
    CAPABILITY_GAP = "capability_gap"


class StepExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class CompletionStatus(str, Enum):
    COMPLETE = "complete"
    NEEDS_REPLAN = "needs_replan"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    WAITING = "waiting"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    INCOMPLETE = "incomplete"


ALLOWED_TRANSITIONS: Set[Tuple[TaskLoopState, TaskLoopState]] = {
    (TaskLoopState.EXECUTING, TaskLoopState.REFLECTING),
    (TaskLoopState.EXECUTING, TaskLoopState.WAITING),
    (TaskLoopState.EXECUTING, TaskLoopState.BLOCKED),
    (TaskLoopState.EXECUTING, TaskLoopState.CANCELLED),
    (TaskLoopState.REFLECTING, TaskLoopState.EXECUTING),
    (TaskLoopState.REFLECTING, TaskLoopState.REPLANNING),
    (TaskLoopState.REFLECTING, TaskLoopState.COMPLETED),
    (TaskLoopState.REFLECTING, TaskLoopState.WAITING),
    (TaskLoopState.REFLECTING, TaskLoopState.BLOCKED),
    (TaskLoopState.REPLANNING, TaskLoopState.EXECUTING),
    (TaskLoopState.REPLANNING, TaskLoopState.COMPLETED),
    (TaskLoopState.REPLANNING, TaskLoopState.BLOCKED),
    (TaskLoopState.COMPLETED, TaskLoopState.REPLANNING),
    (TaskLoopState.COMPLETED, TaskLoopState.BLOCKED),
    (TaskLoopState.WAITING, TaskLoopState.EXECUTING),
    (TaskLoopState.WAITING, TaskLoopState.CANCELLED),
}


@dataclass(frozen=True)
class EvidenceArtifact:
    """Typisiertes Artifact eines ausgeführten Steps.

    artifact_type: z. B. "tool_result", "semantic_search_result", "file_content".
    Entspricht dem artifact_type-Feld aus document_resolution.collect_result_artifacts().
    """

    step_id: str
    artifact_type: str
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvidenceArtifact":
        """Konvertiert ein bestehendes Dict-Artifact in EvidenceArtifact."""
        metadata = _artifact_metadata(d)
        return cls(
            step_id=str(d.get("source_step_id") or d.get("step_id") or ""),
            artifact_type=str(d.get("artifact_type") or "tool_result"),
            content=str(d.get("result") or d.get("output") or d.get("content") or ""),
            metadata=metadata,
        )


def _artifact_metadata(d: Dict[str, Any]) -> Dict[str, Any]:
    raw = d.get("metadata")
    if isinstance(raw, dict):
        flat = {k: v for k, v in raw.items() if k != "metadata"}
        if flat:
            return flat
        nested = raw.get("metadata")
        if isinstance(nested, dict):
            return dict(nested)
        return {}
    return {
        k: v
        for k, v in d.items()
        if k not in {"source_step_id", "step_id", "artifact_type", "result", "output", "content"}
    }


@dataclass(frozen=True)
class StepExecutionResult:
    step_id: str
    status: StepExecutionStatus
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    tool_call_started: bool = False
    receipt: Optional[StepOperationReceipt] = None


@dataclass(frozen=True)
class StepOperationExecution:
    """Persisted receipt plus the executor's actual status."""

    receipt: StepOperationReceipt
    status: StepExecutionStatus


@dataclass(frozen=True)
class TaskLoopSnapshot:
    plan_id: str
    conversation_id: str
    objective: str
    state: TaskLoopState
    current_step_index: int
    max_steps: int
    max_retries_per_step: int
    total_steps: int = 0
    tool_calls: int = 0
    max_total_steps: Optional[int] = None
    max_tool_calls: Optional[int] = None
    deadline_ts: Optional[float] = None
    replan_count: int = 0
    max_replans: int = 0
    loop_detection_enabled: bool = True
    no_progress_threshold: int = 3
    approval_mode: str = "risk_based"
    failure_escalation: str = "replan"
    approval_required_tools: List[str] = field(default_factory=list)
    completed_steps: List[str] = field(default_factory=list)
    pending_step: str = ""
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    stop_reason: Optional[StopReason] = None
    waiting_reason: Optional[str] = None
    waiting_source: Optional[str] = None
    error_count: int = 0
    retry_counts: Dict[str, int] = field(default_factory=dict)
    progress_signature: str = ""
    no_progress_count: int = 0
    previous_state: Optional[TaskLoopState] = None
    step_operation_executions: List[StepOperationExecution] = field(default_factory=list)

    def can_transition_to(self, next_state: TaskLoopState) -> bool:
        return (self.state, next_state) in ALLOWED_TRANSITIONS

    def transition_to(self, next_state: TaskLoopState, **updates: Any) -> "TaskLoopSnapshot":
        if not self.can_transition_to(next_state):
            raise ValueError(f"Invalid task loop transition: {self.state.value} -> {next_state.value}")
        return replace(self, state=next_state, previous_state=self.state, **updates)


@dataclass(frozen=True)
class TaskLoopResult:
    state: TaskLoopState
    stop_reason: Optional[StopReason]
    artifacts: List[Dict[str, Any]]
    visible_content: str
    snapshot: TaskLoopSnapshot
    completion_status: CompletionStatus = CompletionStatus.INCOMPLETE
    active_plan: Any = None
