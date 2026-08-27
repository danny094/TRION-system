from dashboard_views import get_dashboard_overview


def dashboard_overview() -> dict:
    """Aggregate commander runtime inventory into a dashboard-shaped read model."""
    return get_dashboard_overview()


def register(mcp) -> None:
    mcp.tool(dashboard_overview)
