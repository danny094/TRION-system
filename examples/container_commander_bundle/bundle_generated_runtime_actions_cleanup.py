#!/usr/bin/env python3

from bundle_runtime_actions import runtime_cleanup_all as runtime_cleanup_all_view, remove_stopped_container as runtime_remove_stopped_container

def runtime_cleanup_all() -> dict:
    """Stop and remove all TRION-managed containers."""
    return runtime_cleanup_all_view()

def remove_stopped_container(container_id: str = "", container_name: str = "") -> dict:
    """Remove one stopped TRION-managed container."""
    return runtime_remove_stopped_container(container_id=container_id, container_name=container_name)
