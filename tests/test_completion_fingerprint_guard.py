import asyncio
import importlib.util
import sys
from pathlib import Path

from adapters.task_resume_serialization import plan_to_dict, snapshot_to_dict
from core.task_loop.contracts import EvidenceArtifact, TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.task_loop.outcome_evaluator import OutcomeAction, evaluate
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.canonical_tool_raw import canonical_raw_tool
from tests.operation_contract_context import canonical_contract_context

ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="inspect",
        steps=[
            PlanStep(
                step_id="s1",
                title="Inspect",
                goal="Inspect runtime",
                tool="container_inspect",
                required_evidence=["runtime_status"],
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="plan-1",
    )


def _artifact(**metadata) -> EvidenceArtifact:
    return EvidenceArtifact(
        step_id="s1",
        artifact_type="runtime_status",
        content="ok",
        metadata=dict(metadata),
    )


def _load_tasks_routes():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    spec = importlib.util.spec_from_file_location(
        "trion_tasks_routes_completion_fingerprint",
        ADMIN_API_DIR / "tasks_routes.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _tool_detail() -> dict:
    return canonical_raw_tool(
        "container_inspect", "container_runtime", "inspect", evidence=["runtime_status"],
        required=[], scopes=["runtime_state"],
    )


def test_required_evidence_counts_with_matching_fingerprint():
    artifact = _artifact(validated_evidence=True, operation_contract_fingerprint="fp")

    decision = evaluate(_plan(), [artifact], expected_operation_contract_fingerprint="fp")

    assert decision.action == OutcomeAction.COMPLETE


def test_required_evidence_replans_on_wrong_fingerprint():
    artifact = _artifact(validated_evidence=True, operation_contract_fingerprint="other")

    decision = evaluate(_plan(), [artifact], expected_operation_contract_fingerprint="fp")

    assert decision.action == OutcomeAction.REPLAN


def test_required_evidence_replans_without_validated_evidence():
    artifact = _artifact(operation_contract_fingerprint="fp")

    decision = evaluate(_plan(), [artifact], expected_operation_contract_fingerprint="fp")

    assert decision.action == OutcomeAction.REPLAN


def test_required_evidence_replans_without_expected_fingerprint():
    artifact = _artifact(validated_evidence=True, operation_contract_fingerprint="fp")

    decision = evaluate(_plan(), [artifact])

    assert decision.action == OutcomeAction.REPLAN


def test_legacy_dict_artifact_without_fingerprint_does_not_complete():
    artifact = EvidenceArtifact.from_dict(
        {
            "source_step_id": "s1",
            "artifact_type": "runtime_status",
            "content": "ok",
        }
    )

    decision = evaluate(_plan(), [artifact], expected_operation_contract_fingerprint="fp")

    assert decision.action == OutcomeAction.REPLAN


def test_approve_passes_stored_fingerprint_to_continue(monkeypatch):
    tasks_routes = _load_tasks_routes()
    snapshot = TaskLoopSnapshot(
        plan_id="plan-1",
        conversation_id="conv",
        objective="Inspect runtime",
        state=TaskLoopState.WAITING,
        current_step_index=0,
        max_steps=5,
        max_retries_per_step=0,
    )
    contract_context = canonical_contract_context(
        primary_operation="inspect", allowed_operations=("inspect",), allowed_transitions=(),
        required_evidence=("runtime_status",),
    )
    fingerprint = contract_context["routing_frame"]["operation_contract_fingerprint"]
    record = {
        "task_id": "task-fp",
        "status": "waiting",
        "plan": plan_to_dict(_plan()),
        "snapshot": snapshot_to_dict(snapshot),
        "orchestrator_context": {
            "orchestrator": {
                "available_tool_details": [_tool_detail()],
                "context": {"routing_frame": contract_context["routing_frame"]},
            },
        },
        "operation_contract_fingerprint": fingerprint,
    }
    seen = {}

    def continue_task_loop(*_args, **kwargs):
        seen.update(kwargs)
        return TaskLoopResult(
            state=TaskLoopState.COMPLETED,
            stop_reason=None,
            artifacts=[],
            visible_content="done",
            snapshot=snapshot,
        )

    monkeypatch.setattr(tasks_routes, "get_task_record", lambda _task_id: record)
    monkeypatch.setattr(tasks_routes, "claim_waiting_task", lambda _task_id, **_kwargs: record)
    monkeypatch.setattr(tasks_routes, "get_available_tools", lambda: [_tool_detail()])
    monkeypatch.setattr(tasks_routes, "continue_task_loop", continue_task_loop)
    monkeypatch.setattr(tasks_routes, "finalize_claimed_task", lambda _task_id, _result, **_kwargs: {})

    asyncio.run(tasks_routes.approve_task("task-fp", tasks_routes.TaskApproveRequest()))

    assert seen["operation_contract_fingerprint"] == fingerprint
