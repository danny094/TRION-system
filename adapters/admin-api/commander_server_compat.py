"""
Shared legacy Container Commander MCP server helpers.

This module is the local truth for the remaining repo-compat tool wrappers.
Historically these wrappers were registered by a vendor compat entry point
that has since been fully removed (see ADR-2026-06-07,
docs/implementation-plans/completed/47-adr-vendor-container-commander-removal-2026-06-07.md).
"""

from __future__ import annotations


def blueprint_summary(bp) -> dict:
    version = str(getattr(bp, "updated_at", "") or getattr(bp, "created_at", "") or "")
    return {
        "blueprint_id": str(getattr(bp, "id", "") or ""),
        "name": str(getattr(bp, "name", "") or ""),
        "description": str(getattr(bp, "description", "") or ""),
        "version": version,
    }


def blueprint_detail(bp) -> dict:
    definition = bp.model_dump() if hasattr(bp, "model_dump") else dict(bp or {})
    return {
        "blueprint_id": str(getattr(bp, "id", "") or definition.get("id") or ""),
        "name": str(getattr(bp, "name", "") or definition.get("name") or ""),
        "description": str(getattr(bp, "description", "") or definition.get("description") or ""),
        "version": str(getattr(bp, "updated_at", "") or getattr(bp, "created_at", "") or ""),
        "definition": definition,
    }


def deploy_container(blueprint_id: str, overrides: dict = None) -> dict:
    """Deployed einen Container aus einem Blueprint."""
    from commander_container_lifecycle import start_container

    instance = start_container(blueprint_id, **(overrides or {}))
    return instance.model_dump() if hasattr(instance, "model_dump") else instance


def stop_container(container_id: str) -> dict:
    """Stoppt einen laufenden Container."""
    from commander_api.mcp_runtime import stop_container_via_mcp

    result = stop_container_via_mcp(container_id)
    return {"stopped": bool(result.get("stopped")), **result}


def exec_in_container(container_id: str, command: str) -> dict:
    """Fuehrt einen Befehl in einem laufenden Container aus."""
    from commander_container_runtime import exec_in_container_detailed

    return exec_in_container_detailed(container_id, command)


def container_logs(container_id: str, tail: int = 100) -> dict:
    """Gibt die letzten Log-Zeilen eines Containers zurueck."""
    from commander_container_runtime import get_container_logs

    return {"logs": get_container_logs(container_id, tail=tail)}


def container_stats(container_id: str) -> dict:
    """CPU/RAM-Auslastung eines Containers."""
    from commander_container_runtime import get_container_stats

    return dict(get_container_stats(container_id) or {})


def container_list() -> dict:
    """Listet alle aktiven TRION-Container."""
    from commander_api.mcp_runtime import list_containers_via_mcp

    return {"containers": list_containers_via_mcp()}


def container_inspect(container_id: str) -> dict:
    """Detaillierte Infos ueber einen Container."""
    from commander_api.mcp_runtime import inspect_container_via_mcp

    return inspect_container_via_mcp(container_id)


def blueprint_list(tags: list = None) -> dict:
    """Listet verfuegbare Blueprints."""
    from commander_deploy_blueprints import list_blueprints

    blueprints = list_blueprints()
    if tags:
        wanted = {str(tag or "").strip().lower() for tag in list(tags or []) if str(tag or "").strip()}
        if wanted:
            blueprints = [
                bp
                for bp in blueprints
                if wanted.intersection(
                    {str(item or "").strip().lower() for item in list(getattr(bp, "tags", []) or [])}
                )
            ]
    return {"blueprints": [blueprint_summary(bp) for bp in blueprints]}


def blueprint_get(blueprint_id: str) -> dict:
    """Gibt Details zu einem Blueprint zurueck."""
    from commander_deploy_blueprints import get_blueprint

    bp = get_blueprint(blueprint_id)
    if not bp:
        return {"error": f"Blueprint '{blueprint_id}' not found"}
    return {"blueprint": blueprint_detail(bp)}


def blueprint_create(blueprint: dict) -> dict:
    """Erstellt einen neuen Blueprint."""
    from commander_blueprint_write import create_blueprint

    return create_blueprint(blueprint)


def blueprint_update(blueprint_id: str, updates: dict) -> dict:
    """Aktualisiert einen bestehenden Blueprint."""
    from commander_blueprint_write import update_blueprint

    return update_blueprint(blueprint_id, updates)


def blueprint_delete(blueprint_id: str) -> dict:
    """Loescht einen Blueprint."""
    from commander_blueprint_write import delete_blueprint

    return delete_blueprint(blueprint_id)


def hardware_resolve(blueprint_id: str, intent: dict = None) -> dict:
    """Loest Hardware-Anforderungen fuer einen Blueprint auf."""
    from commander_deploy_blueprints import resolve_blueprint
    from commander_deploy_hardware import resolve_for_deploy

    bp = resolve_blueprint(blueprint_id)
    if not bp:
        return {"error": f"Blueprint '{blueprint_id}' not found"}
    resolution = resolve_for_deploy(blueprint_id=blueprint_id, intents=list(bp.hardware_intents or []))
    return resolution.model_dump()


def hardware_preview(blueprint_id: str) -> dict:
    """Vorschau der Hardware-Aufloesung ohne Deployment."""
    from commander_deploy_blueprints import resolve_blueprint
    from commander_deploy_hardware import resolve_for_deploy
    from commander_hardware_resolution import build_hardware_resolution_preview_payload

    bp = resolve_blueprint(blueprint_id)
    if not bp:
        return {"error": f"Blueprint '{blueprint_id}' not found"}
    resolution = resolve_for_deploy(blueprint_id=blueprint_id, intents=list(bp.hardware_intents or []))
    return build_hardware_resolution_preview_payload(resolution)


def storage_provision(container_id: str, scope: str, path: str) -> dict:
    """Provisioniert Storage fuer einen Container."""
    from commander_storage_scope_store import provision_storage

    return provision_storage(container_id, scope, path)


def approval_request(action: str, payload: dict) -> dict:
    """Fordert User-Freigabe fuer eine riskante Aktion an."""
    from commander_approval_compat import request_legacy_approval

    return request_legacy_approval(action, payload)


def approval_status(approval_id: str) -> dict:
    """Prueft den Status einer ausstehenden Freigabe."""
    from commander_approval_store import get_approval

    approval = get_approval(approval_id)
    return approval or {}
