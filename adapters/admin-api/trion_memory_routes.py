"""
Legacy Home-Memory Routes.

Wichtige Abgrenzung:

- Diese Endpunkte werden produktiv ueber den Commander-Namespace
  `/trion/memory/*` gemountet und bedienen den aelteren Home-/Note-Memory-Pfad
  ueber den separaten Admin-API-Store `home_note_memory`.
- Sie sind **nicht** Teil der WebUI-Memory-App unter `/api/memory/*`.
- Sie sind **nicht** an die SQL-Conversation-Policy aus
  `core/conversation_meta/*` oder `memory/memory_mcp/*` gekoppelt.

Solange dieser Router aktiv bleibt, gilt:

- separate Wahrheit
- separater Scope (`identity_path` statt `conversation_id`)
- keine stillschweigende Gleichsetzung mit dem SQL-Memory-Policy-Pfad
"""

from fastapi import APIRouter, Request

from commander_api.common import exception_response
from home_note_memory import MemoryPolicyError, memory_status, recall_notes, recent_notes, remember_note

router = APIRouter(tags=["trion-memory"])


def _memory_error_status(error_code: str) -> int:
    code = str(error_code or "").strip().lower()
    if code == "bad_request":
        return 400
    if code == "policy_denied":
        return 403
    if code in {
        "home_container_missing",
        "home_container_not_running",
        "home_container_ambiguous",
        "home_container_unavailable",
    }:
        return 409
    return 500


@router.post("/remember")
async def api_trion_memory_remember(request: Request):
    try:
        data = await request.json()
        return remember_note(
            content=str(data.get("content", "")),
            category=str(data.get("category", "note")),
            importance=float(data.get("importance", 0.5)),
            trigger=str(data.get("trigger", "auto")),
            context=str(data.get("context", "")),
            why=str(data.get("why", "")),
            identity_path=(str(data.get("identity_path", "")).strip() or None),
        )
    except Exception as e:
        if isinstance(e, MemoryPolicyError):
            return exception_response(
                e,
                status_code=_memory_error_status(e.error_code),
                error_code=e.error_code,
                details=e.details,
            )
        return exception_response(e)


@router.get("/recent")
async def api_trion_memory_recent(limit: int = 20, identity_path: str = ""):
    try:
        return recent_notes(limit=limit, identity_path=(identity_path.strip() or None))
    except Exception as e:
        if isinstance(e, MemoryPolicyError):
            return exception_response(
                e,
                status_code=_memory_error_status(e.error_code),
                error_code=e.error_code,
                details=e.details,
            )
        return exception_response(e)


@router.get("/recall")
async def api_trion_memory_recall(
    query: str = "",
    limit: int = 10,
    category: str = "",
    identity_path: str = "",
):
    try:
        return recall_notes(
            query=query,
            limit=limit,
            category=category,
            identity_path=(identity_path.strip() or None),
        )
    except Exception as e:
        if isinstance(e, MemoryPolicyError):
            return exception_response(
                e,
                status_code=_memory_error_status(e.error_code),
                error_code=e.error_code,
                details=e.details,
            )
        return exception_response(e)


@router.get("/status")
async def api_trion_memory_status(identity_path: str = ""):
    try:
        return memory_status(identity_path=(identity_path.strip() or None))
    except Exception as e:
        if isinstance(e, MemoryPolicyError):
            return exception_response(
                e,
                status_code=_memory_error_status(e.error_code),
                error_code=e.error_code,
                details=e.details,
            )
        return exception_response(e)
