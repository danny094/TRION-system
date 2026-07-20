"""
Shared marketplace blueprint compatibility helpers.

This module is the local truth for the remaining legacy marketplace blueprint
CRUD wrappers that still exist for repo compatibility.
"""

from __future__ import annotations


def get_blueprint_local(blueprint_id: str):
    from commander_deploy_blueprints import get_blueprint

    return get_blueprint(blueprint_id)


def resolve_blueprint_local(blueprint_id: str):
    from commander_deploy_blueprints import resolve_blueprint

    return resolve_blueprint(blueprint_id)


def create_blueprint_local(blueprint):
    from commander_blueprint_write import create_blueprint

    payload = blueprint.model_dump() if hasattr(blueprint, "model_dump") else dict(blueprint or {})
    create_blueprint(payload)
    blueprint_id = str(payload.get("id") or "").strip()
    return get_blueprint_local(blueprint_id) if blueprint_id else None


def update_blueprint_local(blueprint_id: str, updates):
    from commander_blueprint_write import update_blueprint

    payload = updates.model_dump() if hasattr(updates, "model_dump") else dict(updates or {})
    update_blueprint(blueprint_id, payload)
    return get_blueprint_local(blueprint_id)
