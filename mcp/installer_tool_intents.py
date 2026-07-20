"""
mcp.installer_tool_intents
============================
Laden, Normalisieren und Mirror-Projektion von `tool_intents.json` aus einem
MCP-Bundle.

Herausgeloest aus mcp/installer_manifest.py (P11.0 SP0, verhaltensneutraler
Split wegen Ueberschreitung der 200-Zeilen-Grenze aus Doc 07). `load_tool_intents()`
bleibt die reine Bundle-Authoring-Quelle (Schema v1, tolerant). P11.0 SP1
erweitert dieselbe Datei um `build_tool_intent_mirror()`: Schema-v2-
Pflichtfeld-Validierung, eindeutige Toolnamen und Canonical-JSON-SHA256 (kein
Ersatzmodul, keine Umbenennung - siehe
docs/implementation-plans/completed/p11-0-tool-manifest-registry-mirror.md).

Codex SP1-Cross-Check: `requires` ist vorhanden sobald gesetzt (auch leer);
`output_schema` akzeptiert nur den Live-Sentinel `mcp_output_schema`;
unbekannte `schema_version`/leere `bundle_version` sind fail-closed.

`build_tool_intent_mirror()` baut nur die Mirror-Projektion als reine
Funktion. Das atomare Schreiben in die Registry-Datei folgt erst in SP2
(`mcp/installer_registry.py`); diese Datei kennt keine Dateisystem-Zielpfade
fuer den Mirror.
"""
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List

from mcp.installer_common import InstallationError

_CAPABILITY_STRING_FIELDS = (
    "domain",
    "operation",
    "risk",
    "freshness_support",
    "tool_role",
)
_CAPABILITY_LIST_FIELDS = (
    "supports_entities",
    "evidence_types",
    "requires",
    "target_scopes",
)

# Bekannte tool_intents.json-Schema-Versionen; unbekannte Werte sind
# fail-closed (Default-Block statt Fallback, P11.0-Plan Zeile 27).
_SUPPORTED_SCHEMA_VERSIONS = (1, 2)

# `requires` zaehlt als vorhanden, sobald der Key gesetzt ist (auch leer).
_PRESENCE_ONLY_CAPABILITY_FIELDS = ("requires",)

# Einziger gueltiger `output_schema`-Wert in Schema v2 (Live-MCP-Sentinel).
_OUTPUT_SCHEMA_SENTINEL = "mcp_output_schema"

# P11-Pflichtfelder (p11-meaning-operation-contract.md, "Tool-Wahrheit").
# Schema v2 markiert unvollstaendige Tools fail-closed statt sie zu
# verwerfen oder unvollstaendig als eligible zu fuehren.
P11_CAPABILITY_FIELDS = (
    "domain",
    "operation",
    "requires",
    "evidence_types",
    "risk",
    "target_scopes",
    "freshness_support",
    "tool_role",
    "output_schema",
)


def load_tool_intents(path: Path) -> Dict[str, Any]:
    import json

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise InstallationError(f"Invalid JSON in {path.name}") from exc
    if not isinstance(payload, dict):
        raise InstallationError(f"{path.name} must contain a JSON object")
    schema_version = int(payload.get("schema_version", 1) or 1)
    tools = payload.get("tools")
    if not isinstance(tools, list) or not tools:
        raise InstallationError("tool_intents.json must contain a non-empty 'tools' list")
    normalized_tools = []
    for raw in tools:
        if not isinstance(raw, dict):
            raise InstallationError("Each tool intent must be a JSON object")
        name = str(raw.get("name", "")).strip()
        description = str(raw.get("description", "")).strip()
        if not name or not description:
            raise InstallationError("Each tool intent requires 'name' and 'description'")
        normalized = {
            "name": name,
            "description": description,
            "examples": _string_list(raw.get("examples"), "examples"),
            "keywords": _string_list(raw.get("keywords"), "keywords"),
        }
        for field in _CAPABILITY_STRING_FIELDS:
            if field in raw:
                normalized[field] = str(raw.get(field) or "").strip()
        if "output_schema" in raw:
            normalized["output_schema"] = _output_schema_reference(raw.get("output_schema"), schema_version)
        for field in _CAPABILITY_LIST_FIELDS:
            if field in raw:
                normalized[field] = _string_list(raw.get(field), field)
        if "can_answer_directly" in raw:
            normalized["can_answer_directly"] = bool(raw.get("can_answer_directly"))
        normalized_tools.append(normalized)
    return {"schema_version": schema_version, "tools": normalized_tools}


def build_tool_intent_mirror(path: Path, bundle_version: str) -> Dict[str, Any]:
    """Baut die vollstaendige Registry-Mirror-Projektion aus einem Bundle.

    P11.0 SP1: validiert eindeutige Toolnamen, markiert bei Schema v2
    unvollstaendige Tools fail-closed (`capability_complete=False` plus
    `missing_capability_fields`) und denormalisiert die Mirror-Metadaten
    (`schema_version`, `source_sha256`, `bundle_version`) pro Tool als
    `tool_intent_meta`. Legacy v1 bleibt unmarkiert lesbar. Der Mirror wird
    immer vollstaendig aus dem Bundle erzeugt, niemals partiell gemergt.
    """
    loaded = load_tool_intents(path)
    if loaded["schema_version"] not in _SUPPORTED_SCHEMA_VERSIONS:
        raise InstallationError(
            f"Unsupported tool_intents.json schema_version: {loaded['schema_version']!r} "
            f"(supported: {_SUPPORTED_SCHEMA_VERSIONS})"
        )
    bundle_version_str = str(bundle_version or "").strip()
    if not bundle_version_str:
        raise InstallationError("build_tool_intent_mirror requires a non-empty bundle_version")
    _assert_unique_tool_names(loaded["tools"])
    source_sha256 = canonical_json_sha256(loaded)
    meta = {
        "schema_version": loaded["schema_version"],
        "source_sha256": source_sha256,
        "bundle_version": bundle_version_str,
    }
    return {
        "schema_version": loaded["schema_version"],
        "source_sha256": source_sha256,
        "bundle_version": meta["bundle_version"],
        "tools": [project_tool(tool, loaded["schema_version"], meta) for tool in loaded["tools"]],
    }


def canonical_json_sha256(payload: Dict[str, Any]) -> str:
    import json

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _assert_unique_tool_names(tools: List[Dict[str, Any]]) -> None:
    seen: set[str] = set()
    for tool in tools:
        name = tool.get("name")
        if name in seen:
            raise InstallationError(f"Duplicate tool name in tool_intents.json: '{name}'")
        seen.add(name)


def project_tool(tool: Dict[str, Any], schema_version: int, meta: Dict[str, Any]) -> Dict[str, Any]:
    projected = dict(tool)
    projected["tool_intent_meta"] = dict(meta)
    if schema_version >= 2:
        missing = [field for field in P11_CAPABILITY_FIELDS if _capability_field_missing(projected, field)]
        projected["capability_complete"] = not missing
        if missing:
            projected["missing_capability_fields"] = missing
    return projected


def _capability_field_missing(projected: Dict[str, Any], field: str) -> bool:
    if field in _PRESENCE_ONLY_CAPABILITY_FIELDS:
        return field not in projected
    return not projected.get(field)


def _output_schema_reference(value: Any, schema_version: int) -> str:
    """Referenz statt Duplikat gilt fuer alle Versionen: kein eingebettetes
    Schema-Objekt. Ab v2 zusaetzlich nur der Sentinel `mcp_output_schema`
    (Live-MCP-outputSchema verwenden). v1 bleibt fuer beliebige Strings tolerant.
    """
    if isinstance(value, (dict, list)):
        raise InstallationError("Field 'output_schema' must be a string reference, not an embedded schema object")
    result = str(value or "").strip()
    if schema_version >= 2 and result and result != _OUTPUT_SCHEMA_SENTINEL:
        raise InstallationError(
            f"Field 'output_schema' must be the literal '{_OUTPUT_SCHEMA_SENTINEL}' "
            f"sentinel (live MCP outputSchema), got: {result!r}"
        )
    return result


def _string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise InstallationError(f"Field '{field_name}' in tool_intents.json must be a list")
    result = [str(item).strip() for item in value if str(item).strip()]
    return result
