from blueprint_store import get_blueprint, list_blueprints
from blueprint_write import create_blueprint, delete_blueprint, export_blueprint_yaml, import_blueprint_yaml, update_blueprint


def blueprint_list() -> dict:
    """List blueprints with the v2 summary shape."""
    return list_blueprints()


def blueprint_get(blueprint_id: str) -> dict:
    """Get one blueprint with the v2 detail shape."""
    return get_blueprint(blueprint_id)


def blueprint_create(blueprint: dict) -> dict:
    """Create one blueprint in the commander store."""
    return create_blueprint(blueprint)


def blueprint_update(blueprint_id: str, updates: dict) -> dict:
    """Update one blueprint in the commander store."""
    return update_blueprint(blueprint_id, updates)


def blueprint_delete(blueprint_id: str) -> dict:
    """Soft-delete one blueprint in the commander store."""
    return delete_blueprint(blueprint_id)


def blueprint_import_yaml(yaml: str) -> dict:
    """Import one blueprint from YAML."""
    return import_blueprint_yaml(yaml)


def blueprint_export_yaml(blueprint_id: str) -> dict:
    """Export one blueprint as YAML."""
    return export_blueprint_yaml(blueprint_id)


def register(mcp) -> None:
    mcp.tool(blueprint_list)
    mcp.tool(blueprint_get)
    mcp.tool(blueprint_create)
    mcp.tool(blueprint_update)
    mcp.tool(blueprint_delete)
    mcp.tool(blueprint_import_yaml)
    mcp.tool(blueprint_export_yaml)
