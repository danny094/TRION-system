"""Shared Test-Helper fuer fachlich verfuegbare Raw-Tool-Fixtures.

P11.0 SP4 Korrektur (Round 2): Eligibility ist eine gemeinsame Predicate-
Funktion - core/orchestrator/tool_descriptor_projection.py::is_eligible_tool_intent().
adapters/tool_runner_bridge.py::get_available_tools() wendet sie als
primaerer Chokepoint auf Live-Tools an; descriptor_from_raw() nutzt dieselbe
Funktion als Fail-closed-Guard. Eligible heisst: `tool_intent_meta` existiert
mit bekannter `schema_version` (1 oder 2), gueltigem `source_sha256`
(64-stelliger Hex-SHA256) und nicht-leerer `bundle_version`; Schema v2
braucht zusaetzlich `capability_complete is True`. Ein Tool ohne (auch nur
minimalen) gueltigen `tool_intent_meta`-Eintrag ist nicht eligible und
erscheint nicht in `available_tools`.

Tests, die ein Tool als fachlich verfuegbar simulieren wollen (Auswahl-/
Policy-Logik, nicht die Eligibility-Grenze selbst), nutzen diese Factory
statt Intent-Dicts pro Test zu duplizieren. Tests, die fehlende Eligibility
gezielt pruefen, bauen ihr Raw-Tool-Dict bewusst ohne `tool_intent_meta`.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Gueltiger, minimaler v1-Mirror-Eintrag fuer Test-Fixtures. v1 braucht kein
# `capability_complete` (siehe is_eligible_tool_intent()).
_VALID_V1_META: Dict[str, Any] = {
    "schema_version": 1,
    "source_sha256": "a" * 64,
    "bundle_version": "1.0.0-test",
}


def eligible_raw_tool(
    name: str,
    description: str = "",
    mcp: str = "",
    tool_intent: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Raw-Tool-Dict mit minimalem, gueltigem Mirror-Eintrag (eligible)."""
    intent: Dict[str, Any] = {
        "name": name,
        "description": description,
        "tool_intent_meta": dict(_VALID_V1_META),
    }
    if tool_intent:
        intent.update(tool_intent)
    return {"name": name, "description": description, "mcp": mcp, "tool_intent": intent}
