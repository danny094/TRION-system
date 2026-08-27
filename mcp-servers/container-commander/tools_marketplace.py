from marketplace_mutations import export_bundle, import_bundle, install_catalog_blueprint, install_starter
from marketplace_views import get_starters, list_bundles, list_catalog, sync_remote_catalog


def marketplace_bundle_list() -> dict:
    """List exported marketplace bundles from the commander marketplace directory."""
    bundles = list_bundles()
    return {"bundles": bundles, "count": len(bundles)}


def marketplace_starter_list() -> dict:
    """List built-in starter blueprints."""
    starters = get_starters()
    return {"starters": starters, "count": len(starters)}


def marketplace_catalog_list(category: str = "", trusted_only: bool = False) -> dict:
    """List cached catalog entries, optionally filtered by category and trust."""
    return list_catalog(category=category, trusted_only=trusted_only)


def marketplace_catalog_sync(repo_url: str = "", branch: str = "main") -> dict:
    """Refresh the remote blueprint catalog cache from a GitHub-backed index."""
    return sync_remote_catalog(repo_url=repo_url, branch=branch)


def marketplace_starter_install(starter_id: str) -> dict:
    """Install one built-in starter blueprint into the commander store."""
    return install_starter(starter_id)


def marketplace_catalog_install(blueprint_id: str, overwrite: bool = False) -> dict:
    """Install one blueprint from the cached remote catalog."""
    return install_catalog_blueprint(blueprint_id=blueprint_id, overwrite=overwrite)


def marketplace_bundle_export(blueprint_id: str) -> dict:
    """Export one blueprint as a shareable TRION bundle."""
    filename = export_bundle(blueprint_id)
    if not filename:
        return {"exported": False, "blueprint_id": blueprint_id}
    return {"exported": True, "filename": filename}


def marketplace_bundle_import(bundle_bytes_b64: str, filename: str = "", overwrite: bool = False) -> dict:
    """Import one TRION bundle from base64-encoded archive bytes."""
    import base64

    bundle_bytes = base64.b64decode(bundle_bytes_b64.encode("utf-8"))
    result = import_bundle(bundle_bytes, filename=filename, overwrite=overwrite)
    return result if isinstance(result, dict) else {"error": "import_failed"}


def register(mcp) -> None:
    mcp.tool(marketplace_bundle_list)
    mcp.tool(marketplace_starter_list)
    mcp.tool(marketplace_catalog_list)
    mcp.tool(marketplace_catalog_sync)
    mcp.tool(marketplace_starter_install)
    mcp.tool(marketplace_catalog_install)
    mcp.tool(marketplace_bundle_export)
    mcp.tool(marketplace_bundle_import)
