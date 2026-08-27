from __future__ import annotations

from contracts import ContainerReferenceError, normalize_container_reference


def resolve_container_reference(client, container_id: str = "", container_name: str = ""):
    _reference_kind, container_ref = normalize_container_reference(
        container_id=container_id,
        container_name=container_name,
    )
    return client.containers.get(container_ref)
