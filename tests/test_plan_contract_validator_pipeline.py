import asyncio
import json
import importlib.util
from pathlib import Path

from core.output.contracts import OutputResult
from core.pipeline import runner
from core.pipeline.task_loop_stage import build_task_loop_stage
from core.task_loop.contracts import StopReason, TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.task_loop.executor import TaskToolResult
from core.task_loop.task_loop import start_task_loop
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult
from tests._core_pipeline_request_helpers import core_pipeline_request


def _plan(tool: str, plan_id: str = "plan") -> ThinkingPlan:
    return ThinkingPlan(
        intent="run_tools",
        steps=[PlanStep(step_id="s1", title="Step", goal="Run", tool=tool)],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id=plan_id,
    )


def test_initial_plan_unknown_tool_is_rejected_before_verifier(monkeypatch):
    seen = {"verifier": False, "task_loop": False}

    monkeypatch.setattr(runner, "build_plan", lambda *_a, **_k: _plan("ghost_tool"))

    def verifier(*_args, **_kwargs):
        seen["verifier"] = True
        return VerifierResult(verdict=Verdict.APPROVED, reason="should_not_run")

    def task_loop(*_args, **_kwargs):
        seen["task_loop"] = True

    async def output(*_args, **_kwargs):
        return OutputResult(content="should not render")

    monkeypatch.setattr(runner, "verify_plan", verifier)
    response = asyncio.run(
        runner.run_chat(
            core_pipeline_request("Run ghost tool"),
            output_fn=output,
            task_loop_fn=task_loop,
        )
    )

    assert seen == {"verifier": False, "task_loop": False}
    assert response.validation_passed is False
    assert response.done_reason == "rejected"
    assert response.content == "Die Anfrage konnte nicht freigegeben werden."

    path = Path(__file__).resolve().parents[1] / "adapters" / "admin-api" / "chat_stream.py"
    spec = importlib.util.spec_from_file_location("plan_contract_chat_stream", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    lines = [json.loads(line) for line in module.response_to_ndjson(response)]
    assert lines[0]["type"] == "rejected"
    assert lines[0]["error_code"] == "request_rejected"
    assert lines[0]["content"] == "Die Anfrage konnte nicht freigegeben werden."
    assert lines[-1]["done_reason"] == "rejected"
    assert "ghost_tool" not in json.dumps(lines)


def test_replan_unknown_tool_is_not_taken_over_or_executed():
    calls = []
    events = []

    def runner_fn(call):
        calls.append(call.tool_name)
        return TaskToolResult(success=False, error="tool_failed")

    def replanner(*_args, **_kwargs):
        return _plan("ghost_tool", plan_id="replan-ghost")

    result = build_task_loop_stage(
        _plan("allowed_tool", plan_id="initial"),
        conversation_id="conv",
        objective="Run allowed",
        task_loop_fn=start_task_loop,
        tool_runner=runner_fn,
        replanner_fn=replanner,
        max_steps=4,
        max_retries_per_step=0,
        max_replans=1,
        event_sink=lambda payload: events.append(dict(payload)),
        available_tools=[{"name": "allowed_tool", "capability_required_args": []}],
    ).result

    assert calls == ["allowed_tool"]
    assert result.state == TaskLoopState.BLOCKED
    assert result.stop_reason == StopReason.CAPABILITY_GAP
    assert result.snapshot.waiting_reason == "plan_contract_unknown_tool:ghost_tool"
    assert "ghost_tool" not in [event.get("tool_name") for event in events]
