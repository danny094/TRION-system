"""
Chat Routes — TRION chat endpoint for Admin-API.
Accepts LobeChat-compatible format, returns Chat Event Contract NDJSON.
"""
import asyncio
import threading

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from adapters.document_store import (
    semantic_save_document_chunk,
    workspace_save_document_chunk,
)
from adapters.orchestrator_sources import build_context_sources
from adapters.task_resume_events import waiting_result_event_payload
from adapters.task_resume_store import register_waiting_task
from adapters.tool_runner_bridge import get_available_tools, make_tool_runner, project_output_evidence_item
from chat_stream import error_to_ndjson, event_to_ndjson, response_to_ndjson
from core.task_loop.contracts import TaskLoopState
from utils.logger import log_error

router = APIRouter()


def _resolve_request_model(raw_model: str) -> str:
    requested = str(raw_model or "").strip()
    if requested and requested.lower() != "default":
        return requested

    try:
        from utils.settings import ALLOWED_MODEL_KEYS, get_effective_model_settings
        from utils.settings import settings as runtime_settings

        persisted = {
            key: value
            for key, value in getattr(runtime_settings, "settings", {}).items()
            if key in ALLOWED_MODEL_KEYS
        }
        effective = get_effective_model_settings(persisted)
        resolved = str(effective.get("OUTPUT_MODEL", {}).get("value") or "").strip()
        if resolved:
            return resolved
    except Exception:
        pass

    return "default"


@router.post("/api/chat")
async def chat(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    messages_raw = data.get("messages", [])
    if not isinstance(messages_raw, list) or not messages_raw:
        return JSONResponse({"error": "messages[] is required"}, status_code=400)

    model = _resolve_request_model(str(data.get("model") or ""))
    conversation_id = str(data.get("conversation_id") or data.get("session_id") or "global")
    autonomous_mode = bool(data.get("autonomous_mode", False))

    from core.models import CoreChatRequest, Message, MessageRole
    messages = []
    for m in messages_raw:
        role_raw = str((m or {}).get("role", "user") or "user").lower()
        content = str((m or {}).get("content", "") or "")
        try:
            role = MessageRole(role_raw)
        except ValueError:
            role = MessageRole.USER
        messages.append(Message(role=role, content=content))

    core_request = CoreChatRequest(
        model=model,
        messages=messages,
        conversation_id=conversation_id,
        stream=bool(data.get("stream", False)),
        source_adapter="admin-api",
        raw_request=data,
    )

    async def generate():
        queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def emit_progress_event(payload: dict):
            if not isinstance(payload, dict):
                return
            try:
                line = event_to_ndjson(model, conversation_id, payload).encode("utf-8")
                loop.call_soon_threadsafe(queue.put_nowait, line)
            except Exception:
                return

        streamed_any_chunk = {"value": False}

        def emit_content_chunk(chunk: str):
            text = str(chunk or "")
            if not text:
                return
            try:
                line = event_to_ndjson(model, conversation_id, {"type": "content", "content": text}).encode("utf-8")
                loop.call_soon_threadsafe(queue.put_nowait, line)
                streamed_any_chunk["value"] = True
            except Exception:
                return

        def run_chat_worker():
            waiting_event = {}

            try:
                def observe_task_loop(
                    *,
                    plan,
                    task_loop_result,
                    orchestrator_context=None,
                    available_tools=None,
                    tool_truth_source=None,
                ):
                    nonlocal waiting_event
                    if task_loop_result.state != TaskLoopState.WAITING:
                        return
                    try:
                        task_id = register_waiting_task(
                            plan,
                            task_loop_result.snapshot,
                            orchestrator_context=orchestrator_context,
                            available_tools=available_tools,
                            tool_truth_source=tool_truth_source,
                        )
                        waiting_event = waiting_result_event_payload(task_id, task_loop_result)
                    except Exception as exc:
                        log_error(f"[Admin-API] Failed to persist waiting task: {exc}", exc_info=True)

                async def run_chat_async():
                    from core.pipeline.runner import run_chat
                    return await run_chat(
                        core_request,
                        document_workspace_save_fn=workspace_save_document_chunk,
                        document_semantic_save_fn=semantic_save_document_chunk,
                        tool_runner=make_tool_runner(),
                        project_output_evidence_item=project_output_evidence_item,
                        orchestrator_raw_tools=get_available_tools(),
                        orchestrator_context_sources=build_context_sources(),
                        task_loop_observer=observe_task_loop,
                        task_event_sink=emit_progress_event,
                        pipeline_event_sink=emit_progress_event,
                        chunk_sink=emit_content_chunk,
                        autonomous_mode=autonomous_mode,
                    )

                response = asyncio.run(run_chat_async())
                lines = list(response_to_ndjson(response, content_already_streamed=streamed_any_chunk["value"]))
                for idx, line in enumerate(lines):
                    is_done_line = idx == len(lines) - 1
                    if is_done_line and waiting_event:
                        loop.call_soon_threadsafe(
                            queue.put_nowait,
                            event_to_ndjson(response.model, response.conversation_id, waiting_event).encode("utf-8"),
                        )
                    loop.call_soon_threadsafe(queue.put_nowait, line.encode("utf-8"))
            except Exception as exc:
                log_error(f"[Admin-API] Chat error: {exc}")
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    error_to_ndjson(exc, model=model, conversation_id=conversation_id).encode("utf-8"),
                )
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        thread = threading.Thread(target=run_chat_worker, daemon=True)
        thread.start()

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

    return StreamingResponse(generate(), media_type="application/x-ndjson")
