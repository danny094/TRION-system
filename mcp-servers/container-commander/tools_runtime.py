from exec_views import exec_in_container, exec_in_container_detailed
from runtime_views import get_container_logs, get_container_stats, get_runtime_quota, inspect_container, list_containers


def container_list() -> dict:
    """List containers with stable v2 summary fields."""
    return list_containers()


def container_inspect(container_id: str = "", container_name: str = "") -> dict:
    """Inspect one container with stable v2 detail fields."""
    return inspect_container(container_id=container_id, container_name=container_name)


def container_logs(container_id: str = "", tail: int = 200, since: str = "", limit_chars: int = 16000, container_name: str = "") -> dict:
    """Read bounded container logs."""
    return get_container_logs(container_id=container_id, tail=tail, since=since, limit_chars=limit_chars, container_name=container_name)


def container_stats(container_id: str = "", container_name: str = "") -> dict:
    """Read live container resource stats with a stable v2 shape."""
    return get_container_stats(container_id=container_id, container_name=container_name)


def runtime_quota() -> dict:
    """Read runtime session quota limits and current managed usage."""
    return get_runtime_quota()


def container_exec(container_id: str = "", command: str = "", timeout: int = 30, container_name: str = "") -> dict:
    """Execute one bounded command inside a running container."""
    return exec_in_container(container_id=container_id, command=command, timeout=timeout, container_name=container_name)


def container_exec_detailed(container_id: str = "", command: str = "", timeout: int = 30, container_name: str = "") -> dict:
    """Execute one bounded command and return split stdout/stderr details."""
    return exec_in_container_detailed(container_id=container_id, command=command, timeout=timeout, container_name=container_name)


def register(mcp) -> None:
    mcp.tool(container_list)
    mcp.tool(container_inspect)
    mcp.tool(container_logs)
    mcp.tool(container_stats)
    mcp.tool(runtime_quota)
    mcp.tool(container_exec)
    mcp.tool(container_exec_detailed)
