from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CommanderErrorPayload(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ContainerSummary(BaseModel):
    container_id: str
    name: str
    image: str
    status: str
    created_at: str = ""
    managed_by_trion: bool = False
    actions_allowed: bool = False
    protected: bool = False


class ContainerInspect(ContainerSummary):
    blueprint_id: str = ""
    labels: dict[str, str] = Field(default_factory=dict)
    ports: list[dict[str, str]] = Field(default_factory=list)
    mounts: list[str] = Field(default_factory=list)
    runtime_state: dict[str, Any] = Field(default_factory=dict)
    home_scope: dict[str, Any] = Field(default_factory=dict)


class ContainerLogsResult(BaseModel):
    container_id: str
    logs: str
    truncated: bool = False
    tail: int
    since: str = ""
    limit_chars: int


class BlueprintSummary(BaseModel):
    blueprint_id: str
    name: str
    description: str = ""
    version: str = ""


class BlueprintDetail(BlueprintSummary):
    definition: dict[str, Any] = Field(default_factory=dict)


def error_result(code: str, message: str, retryable: bool = False) -> dict[str, Any]:
    return {"ok": False, "error": CommanderErrorPayload(code=code, message=message, retryable=retryable).model_dump()}
