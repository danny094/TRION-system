from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from commander_api.mcp_blueprints import get_blueprint_via_mcp


@dataclass(slots=True)
class HardwareBlueprintView:
    id: str
    hardware_intents: list[dict[str, Any]] = field(default_factory=list)


def _intent_key(intent: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(intent.get("resource_id") or "").strip(),
        str(intent.get("target_type") or "").strip(),
        str(intent.get("target_id") or "").strip(),
        str(intent.get("attachment_mode") or "").strip(),
    )


def _normalize_intents(raw: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in list(raw or []):
        if isinstance(item, dict):
            normalized.append(dict(item))
            continue
        model_dump = getattr(item, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump()
            if isinstance(dumped, dict):
                normalized.append(dict(dumped))
    return normalized


def _definition(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("definition")
    return dict(raw) if isinstance(raw, dict) else {}


def _merge_hardware_intents(parent: list[dict[str, Any]], child: list[dict[str, Any]]) -> list[dict[str, Any]]:
    child_keys = {_intent_key(item) for item in child}
    merged = [dict(item) for item in parent if _intent_key(item) not in child_keys]
    merged.extend(dict(item) for item in child)
    return merged


def load_blueprint_hardware_view(
    blueprint_id: str,
    *,
    resolve: bool = True,
    _visited: set[str] | None = None,
) -> HardwareBlueprintView:
    target_id = str(blueprint_id or "").strip()
    if not target_id:
        raise ValueError("blueprint_id is required")

    payload = get_blueprint_via_mcp(target_id)
    view = HardwareBlueprintView(
        id=str(payload.get("blueprint_id") or target_id).strip() or target_id,
        hardware_intents=_normalize_intents(_definition(payload).get("hardware_intents")),
    )
    if not resolve:
        return view

    definition = _definition(payload)
    parent_id = str(definition.get("extends") or "").strip()
    if not parent_id:
        return view

    visited = set(_visited or set())
    if target_id in visited or parent_id in visited:
        return view
    visited.add(target_id)
    parent = load_blueprint_hardware_view(parent_id, resolve=True, _visited=visited)
    return HardwareBlueprintView(
        id=view.id,
        hardware_intents=_merge_hardware_intents(parent.hardware_intents, view.hardware_intents),
    )
