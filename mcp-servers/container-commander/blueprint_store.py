from __future__ import annotations

import json
import sqlite3
from typing import Any

from contracts import BlueprintDetail, BlueprintSummary, error_result
from blueprint_store_db import ensure_store_initialized, get_conn


def _get_conn() -> sqlite3.Connection:
    return get_conn()


def _row_version(row: sqlite3.Row) -> str:
    updated = str(row["updated_at"] or "").strip()
    created = str(row["created_at"] or "").strip()
    return updated or created


def _blueprint_definition(row: sqlite3.Row) -> dict[str, Any]:
    def load_json(key: str, default: Any) -> Any:
        try:
            return json.loads(row[key] or json.dumps(default))
        except Exception:
            return default

    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"] or "",
        "dockerfile": row["dockerfile"] or "",
        "image": row["image"] or "",
        "runtime": row["runtime"] or "",
        "ports": load_json("ports_json", []),
        "mounts": load_json("mounts_json", []),
        "environment": load_json("environment_json", {}),
        "resources": load_json("resources_json", {}),
        "tags": load_json("tags_json", []),
        "icon": row["icon"] or "📦",
    }


def list_blueprints() -> dict[str, Any]:
    ensure_store_initialized()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT id, name, description, created_at, updated_at FROM blueprints "
            "WHERE (is_deleted IS NULL OR is_deleted = 0) ORDER BY name"
        ).fetchall()
        blueprints = [
            BlueprintSummary(
                blueprint_id=row["id"],
                name=row["name"],
                description=row["description"] or "",
                version=_row_version(row),
            ).model_dump()
            for row in rows
        ]
        return {"blueprints": blueprints}
    except sqlite3.OperationalError:
        return {"blueprints": []}
    finally:
        conn.close()


def get_blueprint(blueprint_id: str) -> dict[str, Any]:
    ensure_store_initialized()
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM blueprints WHERE id = ? AND (is_deleted IS NULL OR is_deleted = 0)",
            (blueprint_id,),
        ).fetchone()
        if not row:
            return error_result("BLUEPRINT_NOT_FOUND", f"Blueprint '{blueprint_id}' not found")
        blueprint = BlueprintDetail(
            blueprint_id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            version=_row_version(row),
            definition=_blueprint_definition(row),
        )
        return {"blueprint": blueprint.model_dump()}
    except sqlite3.OperationalError:
        return error_result("RUNTIME_UNAVAILABLE", "Blueprint store is not initialized", retryable=True)
    finally:
        conn.close()
