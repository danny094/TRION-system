from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


DEFAULT_IDENTITY_PATH = "/home/trion"


@dataclass
class MemoryPolicyError(Exception):
    error_code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return str(self.details.get("error") or self.error_code)


def _store_path() -> Path:
    raw = str(os.getenv("TRION_HOME_NOTE_MEMORY_PATH", "/app/data/trion_home_note_memory.json")).strip()
    return Path(raw or "/app/data/trion_home_note_memory.json")


def _identity_path(identity_path: str | None) -> str:
    value = str(identity_path or "").strip()
    return value or DEFAULT_IDENTITY_PATH


def _load_store() -> dict[str, list[dict[str, Any]]]:
    path = _store_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): list(value or []) for key, value in payload.items()}


def _save_store(store: dict[str, list[dict[str, Any]]]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, ensure_ascii=True, indent=2), encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_limit(value: int, *, default: int, upper: int) -> int:
    try:
        limit = int(value)
    except Exception as exc:
        raise MemoryPolicyError("bad_request", {"error": "limit must be an integer"}) from exc
    if limit <= 0:
        raise MemoryPolicyError("bad_request", {"error": "limit must be > 0"})
    return min(limit, upper)


def _entries_for(identity_path: str | None) -> list[dict[str, Any]]:
    key = _identity_path(identity_path)
    return list(_load_store().get(key, []))


def remember_note(
    *,
    content: str,
    category: str = "note",
    importance: float = 0.5,
    trigger: str = "auto",
    context: str = "",
    why: str = "",
    identity_path: str | None = None,
) -> dict[str, Any]:
    text = str(content or "").strip()
    if not text:
        raise MemoryPolicyError("bad_request", {"error": "content is required"})
    try:
        importance_value = max(0.0, min(1.0, float(importance)))
    except Exception as exc:
        raise MemoryPolicyError("bad_request", {"error": "importance must be numeric"}) from exc

    key = _identity_path(identity_path)
    entry = {
        "id": uuid4().hex,
        "content": text,
        "category": str(category or "note").strip() or "note",
        "importance": importance_value,
        "trigger": str(trigger or "auto").strip() or "auto",
        "context": str(context or "").strip(),
        "why": str(why or "").strip(),
        "identity_path": key,
        "created_at": _utc_now(),
    }
    store = _load_store()
    rows = list(store.get(key, []))
    rows.append(entry)
    store[key] = rows[-500:]
    _save_store(store)
    return {"saved": True, "entry": entry}


def recent_notes(*, limit: int = 20, identity_path: str | None = None) -> dict[str, Any]:
    rows = sorted(_entries_for(identity_path), key=lambda item: str(item.get("created_at") or ""), reverse=True)
    safe_limit = _coerce_limit(limit, default=20, upper=100)
    entries = rows[:safe_limit]
    return {"entries": entries, "count": len(entries), "identity_path": _identity_path(identity_path)}


def recall_notes(
    *,
    query: str = "",
    limit: int = 10,
    category: str = "",
    identity_path: str | None = None,
) -> dict[str, Any]:
    rows = _entries_for(identity_path)
    safe_limit = _coerce_limit(limit, default=10, upper=100)
    query_lower = str(query or "").strip().lower()
    category_lower = str(category or "").strip().lower()

    def _matches(entry: dict[str, Any]) -> bool:
        if category_lower and str(entry.get("category") or "").strip().lower() != category_lower:
            return False
        if not query_lower:
            return True
        haystack = " ".join(
            str(entry.get(key) or "") for key in ("content", "context", "why", "category", "trigger")
        ).lower()
        return query_lower in haystack

    hits = [entry for entry in sorted(rows, key=lambda item: str(item.get("created_at") or ""), reverse=True) if _matches(entry)]
    return {"entries": hits[:safe_limit], "count": min(len(hits), safe_limit), "identity_path": _identity_path(identity_path)}


def memory_status(*, identity_path: str | None = None) -> dict[str, Any]:
    rows = sorted(_entries_for(identity_path), key=lambda item: str(item.get("created_at") or ""), reverse=True)
    categories = sorted({str(item.get("category") or "").strip() for item in rows if str(item.get("category") or "").strip()})
    latest = str(rows[0].get("created_at") or "") if rows else ""
    return {
        "status": "ready",
        "identity_path": _identity_path(identity_path),
        "count": len(rows),
        "categories": categories,
        "latest_created_at": latest,
    }
