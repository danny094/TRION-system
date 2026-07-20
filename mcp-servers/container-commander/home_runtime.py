from __future__ import annotations

from typing import Any

from utils.trion_home_contract import (
    MANIFEST_PATH,
    blueprint_id_from_labels,
    build_home_scope,
    is_home_container,
    parse_home_manifest,
)

# Capability-Klassen, die dieser Container Commander einem Home-Container
# liefert. Bewusst direkt deklariert (Bundle-eigenes Wissen) statt aus einem
# Tool-Namens-Mapping abgeleitet — siehe docs/memory-grounding/34-semantic-tool-truth-drift.md.
COMMANDER_HOME_CAPABILITY_CLASSES = [
    "container_inventory",
    "container_inspect",
    "container_logs",
]


def commander_home_scope(container: Any, labels: dict[str, str]) -> dict[str, Any]:
    if not is_home_container(labels):
        return {}
    manifest = read_home_manifest(container)
    return build_home_scope(
        labels=labels,
        manifest=manifest,
        available_capability_classes=list(COMMANDER_HOME_CAPABILITY_CLASSES),
        verification_sources=["container_inspect"] + (["home_manifest"] if manifest else []),
    )


def home_blueprint_id(labels: dict[str, str]) -> str:
    return blueprint_id_from_labels(labels)


def read_home_manifest(container: Any) -> dict[str, Any]:
    try:
        result = container.exec_run(["cat", MANIFEST_PATH])
    except Exception:
        return {}
    exit_code = getattr(result, "exit_code", None)
    if exit_code is None or int(exit_code) != 0:
        return {}
    output = getattr(result, "output", b"")
    try:
        raw = output.decode("utf-8", errors="replace")
    except Exception:
        return {}
    return parse_home_manifest(raw)
