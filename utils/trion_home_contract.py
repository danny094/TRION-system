from __future__ import annotations

import json
from typing import Any, Iterable

HOME_ROOT = "/home/trion"
MANIFEST_PATH = f"{HOME_ROOT}/.trion/home.json"
DEFAULT_WRITE_ROOTS = [
    f"{HOME_ROOT}/notes",
    f"{HOME_ROOT}/diary",
    f"{HOME_ROOT}/scratch",
    f"{HOME_ROOT}/workspace",
    f"{HOME_ROOT}/artifacts",
]

# Capability-Klassen-Taxonomie: die Klassen, die ein Home-Container fuellen
# kann oder die fuer den Self-Context relevant sind. Reine Klassen-Liste —
# keine Tool-Namen.
HOME_CAPABILITY_CLASSES = [
    "container_inventory",
    "container_inspect",
    "container_logs",
    "file_read",
    "file_list",
    "file_write",
    "file_append",
    "workspace_read",
    "workspace_write",
    "local_exec",
]

# Einzige Quelle der Wahrheit fuer das Mapping
# (tool_intent.domain, tool_intent.operation) -> (capability_class, scope).
#
# Tools liefern (domain, operation) ueber ihre Bundle-tool_intents (Live-
# Discovery). Capability-Klassen werden daraus abgeleitet — keine
# hartcodierten Tool-Namen mehr im Core. Neue MCPs landen automatisch in der
# passenden Klasse, sobald sie ihre tool_intents mit den hier definierten
# (domain, operation)-Werten ausstellen.
#
# Diese Tabelle ersetzt das frühere TOOL_CAPABILITY_MAP, das Tool-Namen wie
# `container_list` direkt auf Capability-Klassen abbildete (siehe
# docs/memory-grounding/34-semantic-tool-truth-drift.md: solche Tool-Behauptungen ausserhalb
# der Runtime-Discovery sind verboten).
DOMAIN_OPERATION_TO_CAPABILITY: dict[tuple[str, str], tuple[str, str]] = {
    ("container_runtime", "list"):    ("container_inventory", "home"),
    ("container_runtime", "inspect"): ("container_inspect", "home"),
    ("container_runtime", "logs"):    ("container_logs", "home"),
    ("workspace", "read"):            ("workspace_read", "home"),
    ("workspace", "write"):           ("workspace_write", "home"),
    ("memory", "read"):               ("memory_read", "agent"),
    ("memory", "write"):              ("memory_write", "agent"),
    ("time", "read"):                 ("time_read", "agent"),
}

CAPABILITY_DESCRIPTIONS = {
    "container_inventory": "laufende oder verfuegbare Container im Runtime-Kontext auflisten",
    "container_inspect": "Container-Metadaten und Runtime-Details pruefen",
    "container_logs": "Container-Logs lesen",
    "file_read": "Dateien im erlaubten Scope lesen",
    "file_list": "Dateien oder Verzeichnisse im erlaubten Scope auflisten",
    "file_write": "Dateien im erlaubten Scope schreiben oder ersetzen",
    "file_append": "Dateien im erlaubten Scope erweitern",
    "workspace_read": "Workspace-Inhalte lesen",
    "workspace_write": "Workspace-Inhalte schreiben",
    "local_exec": "lokale Befehle im erlaubten Scope ausfuehren",
    "memory_read": "kuratierten Memory-Kontext und relevante Erinnerungen lesen",
    "memory_write": "langfristige Erinnerungen oder strukturierte Eintraege speichern",
    "time_read": "aktuelle Zeit- und Datumsinformationen lesen",
}


def is_true(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def blueprint_id_from_labels(labels: dict[str, Any]) -> str:
    return str(labels.get("trion.blueprint") or "").strip()


def is_home_container(labels: dict[str, Any]) -> bool:
    return is_true(labels.get("trion.home")) or str(labels.get("trion.role") or "").strip().lower() == "home"


def parse_home_manifest(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(str(raw or "").strip())
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def capability_class_from_domain_operation(domain: Any, operation: Any) -> tuple[str, str] | None:
    """Leite Capability-Klasse + Scope aus (domain, operation) ab.

    Returns ``(class_name, scope)`` oder ``None`` wenn die Kombination keiner
    Klasse zugeordnet ist. Einzige Quelle: ``DOMAIN_OPERATION_TO_CAPABILITY``.
    """
    key = (str(domain or "").strip().lower(), str(operation or "").strip().lower())
    if not key[0] or not key[1]:
        return None
    return DOMAIN_OPERATION_TO_CAPABILITY.get(key)


def capability_classes_from_intents(intents: Iterable[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Leite available + missing Capability-Klassen aus Tool-Intents ab.

    Erwartet Iterable von Dicts mit Schluesseln ``capability_domain`` und
    ``capability_operation`` (so wie sie aus dem Orchestrator-Tool-Detail
    kommen) oder alternativ ``domain``/``operation`` (so wie sie in
    tool_intents.json eines MCP-Bundles stehen).
    """
    seen: list[str] = []
    for item in intents:
        if not isinstance(item, dict):
            continue
        domain = item.get("capability_domain") if "capability_domain" in item else item.get("domain")
        operation = item.get("capability_operation") if "capability_operation" in item else item.get("operation")
        match = capability_class_from_domain_operation(domain, operation)
        if match is None:
            continue
        name, _scope = match
        if name not in seen:
            seen.append(name)
    missing = [item for item in HOME_CAPABILITY_CLASSES if item not in seen]
    return seen, missing


def capability_description(capability_name: str) -> str:
    return str(CAPABILITY_DESCRIPTIONS.get(str(capability_name or "").strip(), "")).strip()


def build_home_scope(
    *,
    labels: dict[str, Any],
    manifest: dict[str, Any] | None,
    available_capability_classes: list[str],
    verification_sources: list[str],
) -> dict[str, Any]:
    if not is_home_container(labels):
        return {}
    manifest = manifest if isinstance(manifest, dict) else {}
    roots = manifest.get("roots") if isinstance(manifest.get("roots"), dict) else {}
    rules = manifest.get("rules") if isinstance(manifest.get("rules"), dict) else {}
    allowed = list(rules.get("allowed_write_roots") or DEFAULT_WRITE_ROOTS)
    available = list(dict.fromkeys(available_capability_classes))
    missing = [item for item in HOME_CAPABILITY_CLASSES if item not in available]
    return {
        "is_home": True,
        "home_id": str(manifest.get("home_id") or blueprint_id_from_labels(labels) or "trion-home"),
        "blueprint_id": str(manifest.get("blueprint_id") or blueprint_id_from_labels(labels) or "trion-home"),
        "owner_agent": str(manifest.get("owner_agent") or "trion"),
        "runtime_profile": str(labels.get("trion.profile") or manifest.get("runtime_profile") or "trion-home"),
        "home_root": str(roots.get("home") or HOME_ROOT),
        "manifest_path": MANIFEST_PATH,
        "manifest_readable": bool(manifest),
        "allowed_write_roots": [str(item) for item in allowed if str(item).strip()],
        "available_capability_classes": available,
        "missing_capability_classes": missing,
        "verification_sources": [str(item) for item in verification_sources if str(item).strip()],
    }


def is_verified_home_scope(scope: dict[str, Any]) -> bool:
    if not isinstance(scope, dict) or not scope.get("is_home"):
        return False
    if not bool(scope.get("manifest_readable")):
        return False
    if not str(scope.get("home_id") or "").strip():
        return False
    if not str(scope.get("blueprint_id") or "").strip():
        return False
    if not str(scope.get("owner_agent") or "").strip():
        return False
    if not isinstance(scope.get("allowed_write_roots"), list) or not scope.get("allowed_write_roots"):
        return False
    return True
