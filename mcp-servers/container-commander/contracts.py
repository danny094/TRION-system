from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ContainerReferenceError(ValueError):
    pass


PHASE_1_CONTAINER_REFERENCE_NAMES = ("container_inspect", "container_logs")
CONTAINER_REFERENCE_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "container_id": {"type": "string"},
        "container_name": {"type": "string"},
    },
    "oneOf": [
        {
            "required": ["container_id"],
            "properties": {
                "container_id": {"pattern": "\\S"},
                "container_name": {"pattern": "^\\s*$"},
            },
        },
        {
            "required": ["container_name"],
            "properties": {
                "container_id": {"pattern": "^\\s*$"},
                "container_name": {"pattern": "\\S"},
            },
        },
    ],
}


def normalize_container_reference(
    container_id: str = "",
    container_name: str = "",
) -> tuple[str, str]:
    normalized_id = str(container_id or "").strip()
    normalized_name = str(container_name or "").strip()
    if bool(normalized_id) == bool(normalized_name):
        raise ContainerReferenceError(
            "Provide exactly one of container_id or container_name"
        )
    if normalized_id:
        return "container_id", normalized_id
    return "container_name", normalized_name


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
