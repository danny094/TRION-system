import asyncio
import importlib.util
import json
import sys
from pathlib import Path

from core.models import CoreChatResponse
from core.task_loop.contracts import (
    StepExecutionStatus,
    StepOperationExecution,
    TaskLoopResult,
    TaskLoopSnapshot,
    TaskLoopState,
)
from core.task_loop.step_operation_receipt import StepOperationReceipt
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _load_chat_routes():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    spec = importlib.util.spec_from_file_location(
        "trion_chat_routes_for_tests", ADMIN_API_DIR / "chat_routes.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Request:
    async def json(self):
        return {
            "model": "test-model",
            "conversation_id": "EXPECTED_ENVELOPE_CONVERSATION",
            "messages": [{"role": "user", "content": "Bitte weitermachen"}],
            "stream": True,
        }


class _AutonomousRequest(_Request):
    async def json(self):
        return {**await super().json(), "autonomous_mode": True}


def _waiting_result() -> TaskLoopResult:
    receipt = StepOperationReceipt(
        "RECEIPT_STEP_SENTINEL", "RECEIPT_OPERATION_SENTINEL",
        "CONTRACT_FINGERPRINT_SENTINEL", True,
    )
    snapshot = TaskLoopSnapshot(
        plan_id="PLAN_ID_SENTINEL",
        conversation_id="PAYLOAD_CONVERSATION_SENTINEL",
        objective="USER_TEXT_SENTINEL",
        state=TaskLoopState.WAITING,
        current_step_index=1,
        max_steps=5,
        max_retries_per_step=1,
        total_steps=2,
        completed_steps=["COMPLETED_STEP_SENTINEL"],
        pending_step="PENDING_STEP_SENTINEL",
        waiting_reason="WAITING_REASON_PRIVATE_TOOL_SENTINEL",
        waiting_source="WAITING_SOURCE_SENTINEL",
        artifacts=[{
            "artifact_type": "tool_result",
            "target": "TARGET_SENTINEL",
            "scope": "SCOPE_SENTINEL",
            "argument": "ARGUMENT_SENTINEL",
            "output": "OUTPUT_SENTINEL",
            "content": "ARTIFACT_CONTENT_SECRET_SENTINEL",
        }],
        step_operation_executions=[
            StepOperationExecution(receipt=receipt, status=StepExecutionStatus.SUCCESS)
        ],
    )
    return TaskLoopResult(
        state=TaskLoopState.WAITING,
        stop_reason=None,
        artifacts=list(snapshot.artifacts),
        visible_content="waiting",
        snapshot=snapshot,
    )


async def _read_ndjson_lines(response):
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode("utf-8"))
    return [json.loads(line) for line in "".join(chunks).splitlines() if line.strip()]


def test_chat_route_uses_real_waiting_projection_and_minimal_envelope(monkeypatch):
    chat_routes = _load_chat_routes()
    waiting = _waiting_result()
    plan = ThinkingPlan(
        intent="run_tools",
        steps=[PlanStep(
            step_id="PLAN_STEP_SENTINEL", title="Step", goal="Goal",
            tool="PRIVATE_TOOL_SENTINEL", tool_arguments={"secret": "ARGUMENT_SENTINEL"},
        )],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="PLAN_ID_SENTINEL",
    )

    async def fake_run_chat(core_request, **kwargs):
        kwargs["task_loop_observer"](
            plan=plan, task_loop_result=waiting, orchestrator_context={}, available_tools=[]
        )
        return CoreChatResponse(
            model="test-model", content="ok",
            conversation_id="EXPECTED_ENVELOPE_CONVERSATION", done=True, done_reason="stop",
        )

    monkeypatch.setattr("core.pipeline.runner.run_chat", fake_run_chat)
    monkeypatch.setattr(chat_routes, "register_waiting_task", lambda *a, **k: "task-approved")

    response = asyncio.run(chat_routes.chat(_Request()))
    lines = asyncio.run(_read_ndjson_lines(response))
    waiting_event = next(line for line in lines if line["type"] == "task_loop_waiting")
    serialized = json.dumps(lines, sort_keys=True)

    assert waiting_event == {
        "type": "task_loop_waiting", "task_id": "task-approved", "state": "waiting",
        "stop_reason": None, "current_step_index": 1, "total_steps": 2,
        "completed_count": 1, "model": "test-model",
        "conversation_id": "EXPECTED_ENVELOPE_CONVERSATION",
        "created_at": waiting_event["created_at"], "done": False,
    }
    assert all(line["conversation_id"] == "EXPECTED_ENVELOPE_CONVERSATION" for line in lines)
    for sentinel in (
        "PAYLOAD_CONVERSATION_SENTINEL", "PLAN_ID_SENTINEL", "PLAN_STEP_SENTINEL",
        "PENDING_STEP_SENTINEL", "COMPLETED_STEP_SENTINEL", "WAITING_REASON_PRIVATE_TOOL_SENTINEL",
        "WAITING_SOURCE_SENTINEL", "RECEIPT_STEP_SENTINEL", "RECEIPT_OPERATION_SENTINEL",
        "CONTRACT_FINGERPRINT_SENTINEL", "TARGET_SENTINEL", "SCOPE_SENTINEL",
        "ARGUMENT_SENTINEL", "OUTPUT_SENTINEL", "ARTIFACT_CONTENT_SECRET_SENTINEL",
        "USER_TEXT_SENTINEL", "PRIVATE_TOOL_SENTINEL",
    ):
        assert sentinel not in serialized


def test_chat_route_streams_controlled_progress_events(monkeypatch):
    chat_routes = _load_chat_routes()

    async def fake_run_chat(core_request, **kwargs):
        sink = kwargs["task_event_sink"]
        sink({"type": "task_loop_state", "state": "executing", "step_index": 0, "total_steps": 1})
        sink({"type": "tool_start", "timeout_s": 30.0})
        sink({"type": "tool_result", "status": "success", "success": True, "artifact_count": 1})
        return CoreChatResponse(
            model="test-model", content="ok",
            conversation_id="EXPECTED_ENVELOPE_CONVERSATION", done=True, done_reason="stop",
        )

    monkeypatch.setattr("core.pipeline.runner.run_chat", fake_run_chat)
    response = asyncio.run(chat_routes.chat(_Request()))
    lines = asyncio.run(_read_ndjson_lines(response))

    assert [line["type"] for line in lines] == [
        "task_loop_state", "tool_start", "tool_result", "content", "done"
    ]
    assert all(line["conversation_id"] == "EXPECTED_ENVELOPE_CONVERSATION" for line in lines)


def test_chat_route_forwards_autonomous_mode_to_runner(monkeypatch):
    chat_routes = _load_chat_routes()
    seen = {}

    async def fake_run_chat(core_request, **kwargs):
        seen["autonomous_mode"] = kwargs.get("autonomous_mode")
        return CoreChatResponse(
            model="test-model", content="ok",
            conversation_id="EXPECTED_ENVELOPE_CONVERSATION", done=True, done_reason="stop",
        )

    monkeypatch.setattr("core.pipeline.runner.run_chat", fake_run_chat)
    response = asyncio.run(chat_routes.chat(_AutonomousRequest()))
    lines = asyncio.run(_read_ndjson_lines(response))

    assert seen["autonomous_mode"] is True
    assert lines[-1]["type"] == "done"
