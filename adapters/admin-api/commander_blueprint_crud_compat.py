"""Shared blueprint CRUD compatibility helpers."""

from __future__ import annotations

from typing import Any, Optional

from commander_blueprint_seeds import get_active_blueprint_ids
from commander_blueprint_write import create_blueprint as _create_blueprint_dict
from commander_blueprint_write import delete_blueprint as _delete_blueprint_dict
from commander_blueprint_write import update_blueprint as _update_blueprint_dict
from commander_deploy_blueprints import get_blueprint, list_blueprints


def create_blueprint(bp: Any):
    payload = bp.model_dump() if hasattr(bp, "model_dump") else dict(bp or {})
    _create_blueprint_dict(payload)
    created = get_blueprint(str(payload.get("id") or "").strip())
    if created is None:
        raise RuntimeError(f"blueprint_create_failed: {payload.get('id')}")
    return created


def update_blueprint(blueprint_id: str, updates: dict) -> Optional[Any]:
    result = _update_blueprint_dict(blueprint_id, updates)
    if isinstance(result, dict) and result.get("error"):
        return None
    return get_blueprint(blueprint_id)


def delete_blueprint(blueprint_id: str) -> bool:
    result = _delete_blueprint_dict(blueprint_id)
    return bool((result or {}).get("deleted"))
