from __future__ import annotations

from typing import Optional

from commander_blueprint_write import export_blueprint_yaml, import_blueprint_yaml
from commander_deploy_blueprints import get_blueprint


def import_from_yaml(yaml_content: str):
    result = import_blueprint_yaml(yaml_content)
    detail = dict(result.get("blueprint") or {})
    blueprint_id = str(detail.get("blueprint_id") or "")
    if not blueprint_id:
        raise RuntimeError("blueprint_import_failed")
    blueprint = get_blueprint(blueprint_id)
    if blueprint is None:
        raise RuntimeError(f"blueprint_import_failed: {blueprint_id}")
    return blueprint


def export_to_yaml(blueprint_id: str) -> Optional[str]:
    result = export_blueprint_yaml(blueprint_id)
    yaml_str = str(result.get("yaml") or "")
    return yaml_str or None

