import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputResult
from core.pipeline import runner
from core.task_loop.executor import TaskToolResult
from tests._eligible_tool_fixtures import eligible_raw_tool
from tests.test_documententest_support import enable_documententest_chunking, fixture_text

_DOCUMENT_RAW_TOOLS = [
    eligible_raw_tool("workspace_get", "Read workspace entry", "sql-memory"),
    eligible_raw_tool("memory_semantic_search", "Search memory", "sql-memory"),
]


def test_documententest_semantic_question_runs_through_runner_with_search_first(monkeypatch):
    seen = {}

    async def fake_output(output_request, chat_request):
        seen["plan"] = output_request.thinking_plan
        seen["output_context"] = output_request.context
        return OutputResult(content="ok")

    def save_workspace(conversation_id, content, entry_type, source_layer):
        seen.setdefault("workspace", []).append((conversation_id, entry_type, source_layer))
        return 300 + len(seen["workspace"])

    def save_semantic(conversation_id, content, content_type, key, value):
        seen.setdefault("semantic", []).append((conversation_id, content_type, key, value))
        return {"success": True}

    def tool_runner(call):
        if call.tool_name == "memory_semantic_search":
            return TaskToolResult(
                success=True,
                result={"artifacts": [{"id": "semantic-hit", "tool": call.tool_name}], "results": [{"id": "semantic-hit"}]},
            )
        if call.tool_name == "workspace_get":
            return TaskToolResult(
                success=True,
                result={"artifacts": [{"id": f"workspace-{call.arguments['entry_id']}", "tool": call.tool_name}]},
            )
        return TaskToolResult(success=False, error="unexpected_tool")

    enable_documententest_chunking(monkeypatch)
    request = CoreChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content="Was passiert in PREGO!?\n\n" + fixture_text())],
        conversation_id="documententest-semantic",
        source_adapter="pytest",
    )
    response = asyncio.run(
        runner.run_chat(
            request,
            output_fn=fake_output,
            tool_runner=tool_runner,
            orchestrator_raw_tools=_DOCUMENT_RAW_TOOLS,
            document_workspace_save_fn=save_workspace,
            document_semantic_save_fn=save_semantic,
        )
    )

    workspace_steps = [step for step in seen["plan"].steps if step.tool == "workspace_get"]

    assert response.content == "ok"
    assert seen["output_context"]["document_tools"]["tool_mode"] == "semantic_first"
    assert seen["plan"].steps[0].tool == "memory_semantic_search"
    assert workspace_steps
    assert len(workspace_steps) <= 3


def test_documententest_semantic_question_executes_search_then_read_via_task_loop(monkeypatch):
    seen = {"calls": []}

    async def fake_output(output_request, chat_request):
        seen["output_context"] = output_request.context
        return OutputResult(content="ok")

    def save_workspace(conversation_id, content, entry_type, source_layer):
        seen.setdefault("workspace", []).append((conversation_id, entry_type, source_layer))
        return 400 + len(seen["workspace"])

    def save_semantic(conversation_id, content, content_type, key, value):
        seen.setdefault("semantic", []).append((conversation_id, content_type, key, value))
        return {"success": True}

    def tool_runner(call):
        seen["calls"].append((call.tool_name, dict(call.arguments)))
        if call.tool_name == "memory_semantic_search":
            return TaskToolResult(
                success=True,
                result={"artifacts": [{"id": "semantic-hit", "tool": call.tool_name}], "results": [{"id": "semantic-hit"}]},
            )
        if call.tool_name == "workspace_get":
            return TaskToolResult(
                success=True,
                result={"artifacts": [{"id": f"workspace-{call.arguments['entry_id']}", "tool": call.tool_name}]},
            )
        return TaskToolResult(success=False, error="unexpected_tool")

    enable_documententest_chunking(monkeypatch)
    request = CoreChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content="Was passiert in PREGO!?\n\n" + fixture_text())],
        conversation_id="documententest-semantic-exec",
        source_adapter="pytest",
    )
    response = asyncio.run(
        runner.run_chat(
            request,
            output_fn=fake_output,
            tool_runner=tool_runner,
            orchestrator_raw_tools=_DOCUMENT_RAW_TOOLS,
            document_workspace_save_fn=save_workspace,
            document_semantic_save_fn=save_semantic,
        )
    )

    assert response.content == "ok"
    assert seen["calls"][0][0] == "memory_semantic_search"
    assert all(name == "workspace_get" for name, _ in seen["calls"][1:])
    assert seen["output_context"]["task_loop"]["state"] == "completed"
    assert seen["output_context"]["task_loop"]["snapshot"]["completed_steps"][0] == "semantic_search_1"
    assert len(seen["output_context"]["task_loop"]["artifacts"]) >= 2


def test_documententest_semantic_hits_drive_workspace_reads(monkeypatch):
    seen = {"calls": []}

    async def fake_output(output_request, chat_request):
        seen["output_context"] = output_request.context
        return OutputResult(content="ok")

    def save_workspace(conversation_id, content, entry_type, source_layer):
        seen.setdefault("workspace", []).append((conversation_id, entry_type, source_layer))
        return 700 + len(seen["workspace"])

    def save_semantic(conversation_id, content, content_type, key, value):
        seen.setdefault("semantic", []).append((conversation_id, content_type, key, value))
        return {"success": True}

    def tool_runner(call):
        seen["calls"].append((call.tool_name, dict(call.arguments)))
        if call.tool_name == "memory_semantic_search":
            return TaskToolResult(
                success=True,
                result={
                    "results": [
                        {"id": "semantic-1", "metadata": {"value": "chunk_index:1;workspace_entry_id:703"}, "similarity": 0.91},
                        {"id": "semantic-2", "metadata": {"value": "chunk_index:0;workspace_entry_id:701"}, "similarity": 0.88},
                    ],
                    "artifacts": [{"id": "semantic-hit", "tool": call.tool_name}],
                },
            )
        if call.tool_name == "workspace_get":
            return TaskToolResult(
                success=True,
                result={"artifacts": [{"id": f"workspace-{call.arguments['entry_id']}", "tool": call.tool_name}]},
            )
        return TaskToolResult(success=False, error="unexpected_tool")

    enable_documententest_chunking(monkeypatch)
    request = CoreChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content="Was passiert in PREGO!?\n\n" + fixture_text())],
        conversation_id="documententest-dynamic-hits",
        source_adapter="pytest",
    )
    response = asyncio.run(
        runner.run_chat(
            request,
            output_fn=fake_output,
            tool_runner=tool_runner,
            orchestrator_raw_tools=_DOCUMENT_RAW_TOOLS,
            document_workspace_save_fn=save_workspace,
            document_semantic_save_fn=save_semantic,
        )
    )

    workspace_calls = [arguments["entry_id"] for name, arguments in seen["calls"] if name == "workspace_get"]

    assert response.content == "ok"
    assert workspace_calls[:2] == [703, 701]
    assert seen["output_context"]["task_loop"]["state"] == "completed"
