import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputResult
from core.pipeline import runner
from core.task_loop.executor import TaskToolResult
from tests.document_embedding_support import load_embedding_tools, require_embedding_runtime
from tests.test_documententest_support import enable_documententest_chunking, fixture_text


def test_documententest_real_embedding_search_executes_in_task_loop(monkeypatch, tmp_path):
    require_embedding_runtime()
    semantic_save_tool, semantic_search_tool = load_embedding_tools(monkeypatch, tmp_path)
    enable_documententest_chunking(monkeypatch)

    seen = {"calls": [], "workspace": {}, "search_results": []}

    async def fake_output(output_request, chat_request):
        seen["plan"] = output_request.thinking_plan
        seen["output_context"] = output_request.context
        return OutputResult(content="ok")

    def save_workspace(conversation_id, content, entry_type, source_layer):
        entry_id = 500 + len(seen["workspace"]) + 1
        seen["workspace"][entry_id] = {
            "conversation_id": conversation_id,
            "content": content,
            "entry_type": entry_type,
            "source_layer": source_layer,
        }
        return entry_id

    def save_semantic(conversation_id, content, content_type, key, value):
        result = semantic_save_tool(
            conversation_id=conversation_id,
            content=content,
            content_type=content_type,
            key=key,
            value=value,
        )
        assert result["success"] is True
        return result

    def tool_runner(call):
        seen["calls"].append((call.tool_name, dict(call.arguments)))
        if call.tool_name == "memory_semantic_search":
            result = semantic_search_tool(**call.arguments)
            seen["search_results"] = list(result.get("results") or [])
            artifacts = [{"id": f"semantic-{item['id']}", "similarity": item["similarity"]} for item in seen["search_results"][:3]]
            return TaskToolResult(success=True, result={"results": seen["search_results"], "count": result.get("count", 0), "artifacts": artifacts})
        if call.tool_name == "workspace_get":
            entry_id = int(call.arguments["entry_id"])
            record = seen["workspace"].get(entry_id)
            if not record:
                return TaskToolResult(success=False, error=f"missing_workspace_entry:{entry_id}")
            return TaskToolResult(
                success=True,
                result={
                    "entry": {"id": entry_id, **record},
                    "artifacts": [{"id": f"workspace-{entry_id}", "entry_type": record["entry_type"]}],
                },
            )
        return TaskToolResult(success=False, error=f"unexpected_tool:{call.tool_name}")

    request = CoreChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content="Was passiert in PREGO!?\n\n" + fixture_text())],
        conversation_id="documententest-embed-int",
        source_adapter="pytest",
    )

    response = asyncio.run(
        runner.run_chat(
            request,
            output_fn=fake_output,
            tool_runner=tool_runner,
            orchestrator_raw_tools=[
                {"name": "workspace_get", "description": "Read workspace entry", "mcp": "sql-memory"},
                {"name": "memory_semantic_search", "description": "Search memory", "mcp": "sql-memory"},
            ],
            document_workspace_save_fn=save_workspace,
            document_semantic_save_fn=save_semantic,
        )
    )

    assert response.content == "ok"
    assert seen["plan"].steps[0].tool == "memory_semantic_search"
    assert seen["calls"][0][0] == "memory_semantic_search"
    assert seen["calls"][0][1]["conversation_id"] == "documententest-embed-int"
    assert seen["search_results"]
    assert any(
        token in item["content"]
        for item in seen["search_results"]
        for token in ("PREGO", "Carolin", "Ameisen")
    )
    assert all(name == "workspace_get" for name, _ in seen["calls"][1:])
    resolved_entry_ids = [
        int(part.partition(":")[2])
        for item in seen["search_results"]
        for part in str((item.get("metadata") or {}).get("value") or "").split(";")
        if part.startswith("workspace_entry_id:")
    ]
    called_entry_ids = [arguments["entry_id"] for name, arguments in seen["calls"][1:]]
    assert called_entry_ids
    assert called_entry_ids[0] in resolved_entry_ids
    assert seen["output_context"]["task_loop"]["state"] == "completed"
    assert seen["output_context"]["task_loop"]["snapshot"]["completed_steps"][0] == "semantic_search_1"
