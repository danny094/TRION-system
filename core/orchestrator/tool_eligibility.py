"""T_eligible: Contract-vs-ToolDescriptor Eligibility-Gate (P11 SP3, Doc56).

Doc56 ("Tool-Contract und Eligibility"):
    T_eligible = passende Domain, Operation, Evidence, Scope und Risiko
    T_executable_now = T_eligible mit jetzt gebundenen Pflichtargumenten

required_args ist deshalb bewusst KEIN Gate dieser Funktion - das ist
T_executable_now (Plan-SP4, hier nicht vorgezogen). Diese Datei kennt nur
T_eligible: fuenf harte Gates, keine Scoring-Kompensation (Doc56: "Harte
Gates werden nicht durch Scoring kompensiert").

SP3-N/SP3-U (2026-06-29): Die Contract-Eligibility ist Orchestrator-Wiring.
Der Legacy-Pfad ohne operation_contract wurde fail-closed gestellt; diese
Funktion liest weiterhin nur den Contract und ToolDescriptor-Felder, keinen
user_text.

Mutating-Praezisierung (Danny, 2026-06-27, nach Fund des Evidence-Sentinels
"manifestdefiniert"): fuer mutierende Contracts (mutating_action=True) muss
das Tool Domain UND Operation explizit deklarieren (capability_domain/
capability_operation nicht leer) - keine Heuristik-Inferenz fuer
sicherheitsrelevante Freigaben.

Codex SP3-D-Fix (2026-06-28): dieselbe Pflicht gilt jetzt fuer ALLE
Contracts, nicht nur mutierende. Doc56 ("Tool-Contract und Eligibility"):
"Fehlt ein Pflichtfeld, ist das Tool nicht direkt vertragsfaehig;
Keyword-Fallback darf es nicht freigeben." infer_tool_domain()/
infer_tool_operation_family() (Keyword-Heuristik aus Name/Beschreibung/
Quelle) werden hier nicht mehr aufgerufen - das war eine zweite Feldquelle
neben dem Manifest (Schatten-Autoritaet), die SP3-C aufgedeckt hat.
filter_tools_by_constraint() (Altpfad ohne Contract) bleibt davon
unberuehrt, da Doc56 nur den Contract-basierten Pfad fuehrt.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.orchestrator.tool_eligibility_helpers import (
    capability_operation_family,
    target_scope_from_contract,
    tool_has_side_effects,
)
from core.orchestrator.contracts import ToolDescriptor


def eligible_tools_for_contract(
    tools: List[ToolDescriptor],
    contract: Optional[Dict[str, Any]],
) -> List[ToolDescriptor]:
    """T_eligible: Domain, Operation, Evidence, Scope, Risiko als harte Gates.

    Leerer/unvollstaendiger Contract (kein Dict oder primary_operation == "")
    gibt keine Tools frei - dieselbe Fail-closed-Regel wie der bisherige
    tools.py-Gate (Plan-Stop SP2 Aufgabe 6), jetzt als einzige Quelle dafuer.
    required_args wird hier nicht geprueft (siehe Modul-Docstring)."""
    if not isinstance(contract, dict):
        return []
    primary_operation = str(contract.get("primary_operation") or "").strip().lower()
    if not primary_operation:
        return []

    contract_domain = str(contract.get("domain") or "").strip().lower()
    mutating_action = bool(contract.get("mutating_action"))
    # Codex P1-Fix (2026-06-28): kein Fallback auf [primary_operation], wenn
    # allowed_operations fehlt oder leer ist - das wuerde eine fehlende/kaputte
    # Contract-Angabe stillschweigend reparieren statt fail-closed zu blocken.
    # Doc56-Invariante "primary_operation in allowed_operations" ist eine
    # Pflicht des Contracts, keine vom Eligibility-Gate herzustellende.
    raw_allowed = contract.get("allowed_operations")
    if not raw_allowed:
        return []
    allowed_operations = {str(item).strip().lower() for item in raw_allowed if str(item).strip()}
    if primary_operation not in allowed_operations:
        return []
    required_evidence = {
        str(item).strip().lower() for item in (contract.get("required_evidence") or []) if str(item).strip()
    }
    target_scope = target_scope_from_contract(domain=contract_domain, intent_kind="", contract=contract)

    eligible: List[ToolDescriptor] = []
    for tool in tools:
        # Sicherheitsrelevant fuer ALLE Contracts (Codex SP3-D-Fix,
        # 2026-06-28): keine Haystack-/Keyword-Inferenz, nur explizite
        # Manifest-Felder. Vorher galt das nur fuer mutating_action=True.
        tool_domain = str(tool.capability_domain or "").strip().lower()
        tool_operation = str(tool.capability_operation or "").strip().lower()
        if not tool_domain or not tool_operation:
            continue
        tool_family = capability_operation_family(tool_operation)

        if contract_domain and tool_domain != contract_domain:
            continue
        if tool_family not in allowed_operations:
            continue

        evidence_types = {str(item).strip().lower() for item in (tool.capability_evidence_types or [])}
        if required_evidence and not required_evidence.issubset(evidence_types):
            continue

        tool_target_scopes = {
            str(item).strip().lower()
            for item in (tool.capability_target_scopes or [])
            if str(item).strip()
        }
        if target_scope and target_scope not in tool_target_scopes:
            continue

        if tool_has_side_effects(tool) and not mutating_action:
            continue

        eligible.append(tool)
    return eligible
