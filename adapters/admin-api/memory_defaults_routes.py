"""
adapters.admin-api.memory_defaults_routes
=========================================
GET/POST /api/settings/memory/defaults

User-konfigurierbare globale Memory-Defaults fuer neue Conversations.

Persistierte Felder (Codex-Vorgabe):
- memory_mode
- do_not_remember
- max_memory_hits

Bewusst NICHT persistiert (abgeleitet im Backend aus den oben drei plus
``temporary`` der jeweiligen Conversation):
- allow_long_term_write
- allow_global_memory_read

Die UI darf die abgeleiteten Werte als read-only Hinweis anzeigen — der
Endpoint liefert sie deshalb mit, aber nur als Antwort, nicht als Eingabe.
Damit bleibt die Wahrheit pro Konzept genau eine (docs/13 + docs/15).
"""
import os
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from core.conversation_meta.defaults import (
    get_default_do_not_remember,
    get_default_max_memory_hits,
    get_default_memory_mode,
)
from utils.memory_defaults import (
    HARDCODED_DEFAULT_DO_NOT_REMEMBER,
    HARDCODED_DEFAULT_MAX_MEMORY_HITS,
    HARDCODED_DEFAULT_MEMORY_MODE,
    MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY,
    MEMORY_DEFAULT_MAX_MEMORY_HITS_KEY,
    MEMORY_DEFAULT_MODE_KEY,
)
from utils.settings import settings

router = APIRouter(tags=["settings"])

MemoryMode = Literal["global_enabled", "conversation_only", "disabled"]


class MemoryDefaults(BaseModel):
    memory_mode: MemoryMode
    do_not_remember: bool
    max_memory_hits: int = Field(ge=1, le=50)


class MemoryDefaultsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_mode: Optional[MemoryMode] = None
    do_not_remember: Optional[bool] = None
    max_memory_hits: Optional[int] = Field(default=None, ge=1, le=50)


def _effective_defaults() -> Dict[str, Any]:
    return {
        "memory_mode": get_default_memory_mode().value,
        "do_not_remember": get_default_do_not_remember(),
        "max_memory_hits": get_default_max_memory_hits(),
    }


def _derived(values: Dict[str, Any]) -> Dict[str, Any]:
    """Backend-Ableitung der nicht-persistierten Felder.

    Dieselbe Logik wie ``core/conversation_meta/policy.py::build_effective_policy``
    fuer eine fiktive Conversation ohne ``temporary``-Status.
    """
    mode = values.get("memory_mode")
    do_not_remember = bool(values.get("do_not_remember"))
    return {
        "allow_global_memory_read": mode == "global_enabled",
        "allow_long_term_write": mode != "disabled" and not do_not_remember,
    }


def _hardcoded_fallback() -> Dict[str, Any]:
    return {
        "memory_mode": HARDCODED_DEFAULT_MEMORY_MODE,
        "do_not_remember": bool(HARDCODED_DEFAULT_DO_NOT_REMEMBER),
        "max_memory_hits": int(HARDCODED_DEFAULT_MAX_MEMORY_HITS),
    }


def _source_for(key: str) -> str:
    if key in settings.settings:
        return "override"
    if os.getenv(key, "").strip():
        return "env"
    return "default"


@router.get("/api/settings/memory/defaults")
async def get_memory_defaults():
    effective = _effective_defaults()
    return {
        "defaults": effective,
        "derived": _derived(effective),
        "fallback": _hardcoded_fallback(),
        "sources": {
            "memory_mode": _source_for(MEMORY_DEFAULT_MODE_KEY),
            "do_not_remember": _source_for(MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY),
            "max_memory_hits": _source_for(MEMORY_DEFAULT_MAX_MEMORY_HITS_KEY),
        },
    }


@router.post("/api/settings/memory/defaults")
async def update_memory_defaults(update: MemoryDefaultsUpdate):
    payload = update.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=422, detail="No valid fields provided")

    field_to_key = {
        "memory_mode": MEMORY_DEFAULT_MODE_KEY,
        "do_not_remember": MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY,
        "max_memory_hits": MEMORY_DEFAULT_MAX_MEMORY_HITS_KEY,
    }
    saved: Dict[str, Any] = {}
    for field, value in payload.items():
        key = field_to_key[field]
        settings.set(key, value)
        saved[field] = value

    effective = _effective_defaults()
    return {
        "success": True,
        "saved": saved,
        "defaults": effective,
        "derived": _derived(effective),
    }
