import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputResult
from core.output.grounding_state import clear_grounding_state
from core.pipeline import runner
from core.task_loop.contracts import TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.task_loop.executor import TaskToolCall
from tests._core_pipeline_request_helpers import core_pipeline_request


def test_core_followup_time_derivation_skips_second_task_loop(monkeypatch):
    clear_grounding_state()
    task_loop_calls = []
    seen = {}

    def fake_orchestrator(user_text, classifier_result, raw_tools=None, context_sources=None, conversation_id="", **kwargs):
        from core.orchestrator.contracts import OrchestratorPackage, ToolDescriptor

        return OrchestratorPackage(
            available_tools=[ToolDescriptor(name="time_now", description="Return current UTC time and date.")],
            selected_tools=[ToolDescriptor(name="time_now", description="Return current UTC time and date.")],
            context={},
            classifier_result=classifier_result,
        )

    def fake_task_loop(plan, *, conversation_id, objective, tool_runner, max_steps, max_retries_per_step, max_replans):
        task_loop_calls.append({"objective": objective, "plan_id": plan.plan_id, "tools": list(plan.suggested_tools)})
        tool_runner(TaskToolCall(tool_name="time_now", step_id="tool_1"))
        snapshot = TaskLoopSnapshot(
            plan_id=plan.plan_id,
            conversation_id=conversation_id,
            objective=objective,
            state=TaskLoopState.COMPLETED,
            current_step_index=1,
            max_steps=max_steps,
            max_retries_per_step=max_retries_per_step,
            completed_steps=["tool_1"],
            artifacts=[
                {
                    "artifact_type": "tool_result",
                    "tool": "time_now",
                    "source_step_id": "tool_1",
                    "result": '{"utc_iso":"2026-05-12T03:26:51Z"}',
                }
            ],
        )
        return TaskLoopResult(
            state=TaskLoopState.COMPLETED,
            stop_reason=None,
            artifacts=list(snapshot.artifacts),
            visible_content="Task loop completed.",
            snapshot=snapshot,
        )

    async def fake_output(output_request, chat_request):
        seen["last_context"] = output_request.context
        return OutputResult(content="ok")

    response_1 = asyncio.run(
        runner.run_chat(
            core_pipeline_request("Wie viel Uhr ist es gerade?"),
            output_fn=fake_output,
            task_loop_fn=fake_task_loop,
            orchestrator_fn=fake_orchestrator,
            orchestrator_raw_tools=[{"name": "time_now"}],
        )
    )

    followup_request = CoreChatRequest(
        model="test-model",
        messages=[
            Message(role=MessageRole.USER, content="Wie viel Uhr ist es gerade?"),
            Message(role=MessageRole.ASSISTANT, content=response_1.content),
            Message(role=MessageRole.USER, content="Und in einer Stunde?"),
        ],
        conversation_id="p0-test",
        source_adapter="pytest",
    )

    response_2 = asyncio.run(
        runner.run_chat(
            followup_request,
            output_fn=fake_output,
            task_loop_fn=fake_task_loop,
            orchestrator_fn=fake_orchestrator,
            orchestrator_raw_tools=[{"name": "time_now"}],
        )
    )

    assert response_1.content == "ok"
    assert response_2.content == "ok"
    assert len(task_loop_calls) == 1
    assert task_loop_calls[0]["objective"] == "Wie viel Uhr ist es gerade?"
    assert seen["last_context"]["grounding_state"]["grounded_results"][0]["tool_name"] == "time_now"
    clear_grounding_state()
