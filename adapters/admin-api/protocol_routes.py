"""Daily protocol REST endpoints."""

import importlib.util
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

try:
    from protocol_merge import (
        get_lock as _get_lock,
        is_protocol_date_stem as _is_protocol_date_stem,
        load_status,
        merge_entries,
        parse_entries as _parse_entries,
        reconstruct_md as _reconstruct_md,
        save_status,
    )
except ModuleNotFoundError:
    _MODULE_PATH = Path(__file__).resolve().with_name("protocol_merge.py")
    _SPEC = importlib.util.spec_from_file_location("trion_protocol_merge", _MODULE_PATH)
    if _SPEC is None or _SPEC.loader is None:
        raise
    _MODULE = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(_MODULE)
    _get_lock = _MODULE.get_lock
    _is_protocol_date_stem = _MODULE.is_protocol_date_stem
    load_status = _MODULE.load_status
    merge_entries = _MODULE.merge_entries
    _parse_entries = _MODULE.parse_entries
    _reconstruct_md = _MODULE.reconstruct_md
    save_status = _MODULE.save_status

router = APIRouter(prefix="/api/protocol", tags=["protocol"])
PROTOCOL_DIR = Path(os.environ.get("PROTOCOL_DIR", "/app/memory"))
STATUS_FILE = PROTOCOL_DIR / ".protocol_status.json"


def _load_status() -> dict:
    return load_status(STATUS_FILE)


def _save_status(status: dict):
    save_status(STATUS_FILE, status)


@router.get("/list")
async def protocol_list():
    PROTOCOL_DIR.mkdir(parents=True, exist_ok=True)
    status = _load_status()
    dates = []
    for filepath in sorted(PROTOCOL_DIR.glob("*.md"), reverse=True):
        date = filepath.stem
        if not _is_protocol_date_stem(date):
            continue
        entries = _parse_entries(filepath.read_text())
        dates.append({"date": date, "merged": status.get(date, False), "entry_count": len(entries)})
    unmerged = sum(1 for item in dates if not item["merged"] and item["entry_count"] > 0)
    return JSONResponse({"dates": dates, "unmerged_count": unmerged})


@router.get("/today")
async def protocol_today():
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = PROTOCOL_DIR / f"{today}.md"
    if not filepath.exists():
        return JSONResponse({"date": today, "content": "", "entries": [], "entry_count": 0})
    content = filepath.read_text()
    entries = _parse_entries(content)
    return JSONResponse({"date": today, "content": content, "entries": entries, "entry_count": len(entries)})


@router.get("/unmerged-count")
async def protocol_unmerged_count():
    PROTOCOL_DIR.mkdir(parents=True, exist_ok=True)
    status = _load_status()
    count = 0
    for filepath in PROTOCOL_DIR.glob("*.md"):
        date = filepath.stem
        if _is_protocol_date_stem(date) and not status.get(date, False):
            if _parse_entries(filepath.read_text()):
                count += 1
    return JSONResponse({"unmerged_count": count})


@router.get("/{date}")
async def protocol_get(date: str):
    filepath = PROTOCOL_DIR / f"{date}.md"
    if not filepath.exists():
        return JSONResponse({"date": date, "content": "", "entries": [], "entry_count": 0})
    content = filepath.read_text()
    entries = _parse_entries(content)
    return JSONResponse({
        "date": date,
        "content": content,
        "entries": entries,
        "entry_count": len(entries),
        "merged": _load_status().get(date, False),
    })


@router.post("/append")
async def protocol_append(request: Request):
    data = await request.json()
    user_msg = data.get("user_message", "").strip()
    ai_response = data.get("ai_response", "").strip()
    timestamp = data.get("timestamp", datetime.now().isoformat())
    conversation_id = data.get("conversation_id", "")
    session_id = data.get("session_id", "")
    if not user_msg or not ai_response:
        return JSONResponse({"error": "user_message and ai_response required"}, status_code=400)
    date, time_str = timestamp[:10], timestamp[11:16]
    filepath = PROTOCOL_DIR / f"{date}.md"
    PROTOCOL_DIR.mkdir(parents=True, exist_ok=True)
    entry = f"\n## {time_str}\n**User:** {user_msg}\n\n**TRION:** {ai_response}\n\n---\n"
    with _get_lock(filepath):
        if not filepath.exists():
            entry = f"# Tagesprotokoll {date}\n{entry}"
        with open(filepath, "a") as handle:
            handle.write(entry)
    status = _load_status()
    status[date] = False
    _save_status(status)
    return JSONResponse({
        "appended": True,
        "date": date,
        "time": time_str,
        "conversation_id": conversation_id or None,
        "session_id": session_id or None,
    })


@router.put("/{date}")
async def protocol_update(date: str, request: Request):
    content = (await request.json()).get("content", "")
    filepath = PROTOCOL_DIR / f"{date}.md"
    if not content.strip():
        return JSONResponse({"error": "content is required"}, status_code=400)
    with _get_lock(filepath):
        filepath.write_text(content)
    status = _load_status()
    status[date] = False
    _save_status(status)
    return JSONResponse({"updated": True, "date": date})


@router.delete("/{date}/entry/{index}")
async def protocol_delete_entry(date: str, index: int):
    filepath = PROTOCOL_DIR / f"{date}.md"
    if not filepath.exists():
        return JSONResponse({"error": "Protocol not found"}, status_code=404)
    with _get_lock(filepath):
        entries = _parse_entries(filepath.read_text())
        if index < 0 or index >= len(entries):
            return JSONResponse({"error": f"Index {index} out of range (0-{len(entries)-1})"}, status_code=400)
        entries.pop(index)
        filepath.write_text(_reconstruct_md(date, entries)) if entries else filepath.unlink()
    return JSONResponse({"deleted": True, "date": date, "index": index, "remaining": len(entries)})


@router.post("/{date}/merge")
async def protocol_merge(date: str):
    filepath = PROTOCOL_DIR / f"{date}.md"
    if not filepath.exists():
        return JSONResponse({"error": "Protocol not found"}, status_code=404)
    entries = _parse_entries(filepath.read_text())
    if not entries:
        return JSONResponse({"error": "No entries to merge"}, status_code=400)
    from mcp.hub import get_hub
    try:
        merged_count, errors = merge_entries(entries, get_hub)
    except Exception as error:
        return JSONResponse({"error": f"MCP Hub error: {error}"}, status_code=500)
    status = _load_status()
    status[date] = True
    _save_status(status)
    return JSONResponse({"merged": True, "date": date, "entries_merged": merged_count, "errors": errors})


@router.post("/summarize-yesterday")
async def summarize_yesterday_endpoint(request: Request):
    try:
        from core.context_compressor import summarize_yesterday
        body = await request.json() if request.headers.get("content-length", "0") != "0" else {}
        return JSONResponse({"success": True, "ran": await summarize_yesterday(force=body.get("force", False))})
    except Exception as error:
        return JSONResponse({"success": False, "error": str(error)}, status_code=500)


@router.get("/rolling-summary")
async def get_rolling_summary():
    summary_file = PROTOCOL_DIR / "rolling_summary.md"
    if not summary_file.exists():
        return JSONResponse({"content": "", "exists": False})
    content = summary_file.read_text(encoding="utf-8")
    return JSONResponse({"content": content, "exists": True, "size": len(content)})
