#!/usr/bin/env python3

from bundle_runtime_actions import start_stopped_container as runtime_start_stopped_container, stop_container as runtime_stop_container

def start_stopped_container(container_id: str = "", container_name: str = "") -> dict:
    """Start a stopped TRION-managed container."""
    return runtime_start_stopped_container(container_id=container_id, container_name=container_name)

def stop_container(container_id: str = "", container_name: str = "") -> dict:
    """Stop a running TRION-managed container."""
    return runtime_stop_container(container_id=container_id, container_name=container_name)
