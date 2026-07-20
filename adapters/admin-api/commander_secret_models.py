from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class SecretScope(str, Enum):
    GLOBAL = "global"
    BLUEPRINT = "blueprint"


class SecretEntry(BaseModel):
    id: int | None = None
    name: str
    scope: SecretScope = SecretScope.GLOBAL
    blueprint_id: str | None = None
    created_at: str | None = None
    expires_at: str | None = None
