from runtime_actions_views import (
    cleanup_all as runtime_cleanup_all_view,
    remove_stopped_container as runtime_remove_stopped_container,
    start_stopped_container as runtime_start_stopped_container,
    stop_container as runtime_stop_container,
)


def runtime_cleanup_all() -> dict:
    """Stop and remove all TRION-managed containers."""
    return runtime_cleanup_all_view()


def remove_stopped_container(container_id: str = "", container_name: str = "") -> dict:
    """Remove one stopped TRION-managed container."""
    return runtime_remove_stopped_container(container_id=container_id, container_name=container_name)


def start_stopped_container(container_id: str = "", container_name: str = "") -> dict:
    """Start a stopped TRION-managed container."""
    return runtime_start_stopped_container(container_id=container_id, container_name=container_name)


def stop_container(container_id: str = "", container_name: str = "") -> dict:
    """Stop a running TRION-managed container."""
    return runtime_stop_container(container_id=container_id, container_name=container_name)


def register_cleanup(mcp) -> None:
    mcp.tool(runtime_cleanup_all)
    mcp.tool(remove_stopped_container)


def register_lifecycle(mcp) -> None:
    mcp.tool(start_stopped_container)
    mcp.tool(stop_container)
