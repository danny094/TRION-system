from collections.abc import Mapping
from copy import deepcopy
from typing import Any, List, Optional

from core.orchestrator.contracts import ToolDescriptor

# Bekannte tool_intents.json-Schema-Versionen (siehe auch
# mcp.installer_tool_intents._SUPPORTED_SCHEMA_VERSIONS). Unbekannte Werte
# sind fail-closed, nicht tolerant.
_VALID_SCHEMA_VERSIONS = (1, 2)
_SHA256_HEX_LENGTH = 64


def _plain_deepcopy(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain_deepcopy(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_deepcopy(item) for item in value]
    return deepcopy(value)


def is_eligible_tool_intent(tool_intent: Any) -> bool:
    """P11.0 SP4 Korrektur (Round 2): einzige Eligibility-Predicate fuer
    Registry-Mirror-Eintraege. adapters/tool_runner_bridge.py::get_available_tools()
    wendet sie auf Live-Tools an (primaerer Chokepoint - nicht eligible
    Tools erscheinen dort gar nicht erst in orchestrator_raw_tools);
    descriptor_from_raw() (unten) ruft dieselbe Funktion als zusaetzlichen
    Fail-closed-Guard auf jedem Eingang auf, unabhaengig davon ob er die
    Bridge durchlaufen hat. Eine einzige Funktion verhindert, dass beide
    Stellen unbeabsichtigt auseinanderlaufen.

    Eligible heisst: `tool_intent` ist ein nicht-leeres Dict, `tool_intent_meta`
    existiert darin als nicht-leeres Dict mit `schema_version` als echtem
    `int` (nicht `bool`/`float` - in Python gilt `True == 1` und `1.0 == 1`,
    ein reiner `in`-Vergleich waere also typunsicher) aus `_VALID_SCHEMA_VERSIONS`,
    einem echten `str` als 64-stelligem Hex-SHA256 in `source_sha256` und
    einem echten, nicht-leeren `str` in `bundle_version` (kein `str()`-Cast
    auf Zahlen/Dicts - sonst waeren z. B. numerische Hashes oder
    Bundle-Versionen faelschlich gueltig). Schema v2 braucht zusaetzlich
    `capability_complete is True` (explizit, kein truthy-Check) - jeder
    andere Wert (fehlend, `False`, sonstiges) macht das v2-Tool nicht
    eligible. Schema v1 bleibt ohne `capability_complete`-Marker eligible
    (Legacy-Vertrag). Fehlt `tool_intent_meta` komplett oder ist es
    unvollstaendig/typfalsch, ist das Tool nicht eligible - unabhaengig
    davon, ob Capability-Felder gesetzt sind.
    """
    if not isinstance(tool_intent, dict) or not tool_intent:
        return False
    meta = tool_intent.get("tool_intent_meta")
    if not isinstance(meta, dict) or not meta:
        return False
    schema_version = meta.get("schema_version")
    if type(schema_version) is not int or schema_version not in _VALID_SCHEMA_VERSIONS:
        return False
    if not _is_valid_sha256_hex(meta.get("source_sha256")):
        return False
    bundle_version = meta.get("bundle_version")
    if not isinstance(bundle_version, str) or not bundle_version.strip():
        return False
    if schema_version == 2 and tool_intent.get("capability_complete") is not True:
        return False
    return True


def _is_valid_sha256_hex(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip().lower()
    return len(text) == _SHA256_HEX_LENGTH and all(ch in "0123456789abcdef" for ch in text)


def descriptor_from_raw(raw: Any) -> Optional[ToolDescriptor]:
    """P11.0 SP4 Korrektur (Round 2): Eligibility ist eine gemeinsame
    Predicate-Funktion (is_eligible_tool_intent() oben), die sowohl
    get_available_tools() (adapters/tool_runner_bridge.py - primaerer
    Chokepoint, filtert Live-Tools bevor sie ueberhaupt in
    orchestrator_raw_tools erscheinen) als auch diese Funktion (zusaetzlicher
    Fail-closed-Guard fuer jeden Eingang, auch ausserhalb des Bridge-Pfads)
    anwenden - siehe tests/test_tool_intent_truth_source.py und
    tests/test_tool_runner_bridge.py. Ein Tool ohne gueltigen Mirror-Eintrag
    (`tool_intent` leer oder ohne vollstaendige `tool_intent_meta`) oder mit
    einem Schema-v2-Eintrag, der nicht exakt `capability_complete is True`
    setzt (fehlend, `False` oder sonstiger Wert - fail-closed aus
    mcp.installer_tool_intents.project_tool()) liefert hier
    `None` und taucht dadurch in list_available_tools()
    (core/orchestrator/tools.py) gar nicht erst auf - nicht eligible, nicht
    nur mit leeren Capability-Feldern. Legacy-v1-Tools ohne
    `capability_complete`-Marker bleiben eligible, solange sie einen
    vollstaendigen (auch sonst minimalen) Mirror-Eintrag haben.

    P11.0 SP4 Round 4 Korrektur: is_eligible_tool_intent() prueft nur die
    interne Gueltigkeit von `tool_intent_meta` - nicht, ob `tool_intent`
    ueberhaupt zum `name` des Eingangs passt. adapters/tool_runner_bridge.py
    bindet das implizit, weil _tool_intent_for() den Mirror-Eintrag selbst per
    Namens-Lookup zieht; ausserhalb des Bridge-Pfads (z. B.
    core/pipeline/document_tools_stage.py -> list_available_tools() mit
    beliebigen raw_tools) fehlte diese Bindung. Deshalb zusaetzlich unten:
    `tool_intent.get("name")` muss exakt `name` entsprechen, sonst `None` -
    ein gueltiger Mirror-Eintrag fuer ein anderes Tool darf nicht als
    Eligibility-Nachweis fuer dieses Tool durchgehen.
    """
    if isinstance(raw, ToolDescriptor):
        return raw
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    tool_intent = raw.get("tool_intent")
    if not is_eligible_tool_intent(tool_intent):
        return None
    intent_name = str(tool_intent.get("name") or "").strip()
    if intent_name != name:
        return None
    meta = tool_intent.get("tool_intent_meta") or {}
    capability_output_schema = str(tool_intent.get("output_schema") or "").strip()
    live_output_schema = raw.get("outputSchema")
    output_schema = {}
    if meta.get("schema_version") == 2 and capability_output_schema == "mcp_output_schema":
        if not isinstance(live_output_schema, Mapping):
            return None
        output_schema = _plain_deepcopy(live_output_schema)
    return ToolDescriptor(
        name=name,
        description=str(raw.get("description") or "").strip(),
        source=str(raw.get("source") or raw.get("mcp") or raw.get("server") or "").strip(),
        schema=raw.get("inputSchema") if isinstance(raw.get("inputSchema"), dict) else {},
        intent_description=str(tool_intent.get("description") or "").strip(),
        intent_examples=_string_list(tool_intent.get("examples")),
        intent_keywords=_string_list(tool_intent.get("keywords")),
        capability_domain=str(tool_intent.get("domain") or "").strip().lower(),
        capability_operation=str(tool_intent.get("operation") or "").strip().lower(),
        capability_entity_types=_string_list(tool_intent.get("supports_entities")),
        capability_evidence_types=_string_list(tool_intent.get("evidence_types")),
        capability_required_args=_string_list(tool_intent.get("requires")),
        capability_risk=str(tool_intent.get("risk") or "").strip().lower(),
        capability_target_scopes=_string_list(tool_intent.get("target_scopes")),
        capability_freshness_support=str(tool_intent.get("freshness_support") or "").strip().lower(),
        capability_output_schema=capability_output_schema,
        output_schema=output_schema,
        tool_role=str(tool_intent.get("tool_role") or "").strip().lower() or "primary",
        can_answer_directly=bool(tool_intent.get("can_answer_directly") is not False),
        mirror_schema_version=meta.get("schema_version"),
        mirror_source_sha256=str(meta.get("source_sha256") or ""),
        mirror_bundle_version=str(meta.get("bundle_version") or ""),
    )


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
