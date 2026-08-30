"""Taxonomie-Lock: Code-erzeugte target_scope-Werte muessen Teilmenge der in
docs/routing/43b-capability-manifest-taxonomy.md ("Target Scope") gepflegten
Liste sein.

Danny SP3-D-DECIDE (2026-06-28), DECIDE-Wahl 1 (Doc43b ergaenzen statt Code
umbiegen): "time_reference existiert bereits als reale Code-/Test-Wahrheit
und ist fachlich ein eigener Target Scope... SP3-D ergaenzt Doc43b um
time_reference und fuegt einen kleinen Taxonomie-Test oder bestehenden
Target-Scope-Test hinzu, der Code und Doc-Wert zusammenhaelt." Dieser Test
ist genau das: er haelt core/orchestrator/tool_eligibility_helpers.py gegen
die Doc43b-Liste fest - kuenftiger
Drift (neuer Code-Wert ohne Doc-Eintrag) faellt hier rot auf, statt erst beim
naechsten Audit aufzufallen.

Bewusst eigene kleine Datei statt Erweiterung groesserer Contract-/Eligibility-
Tests, damit der Doc07-Cap nicht durch Taxonomie-Lock-Details belastet wird.

Hinweis: dies ist eine Teilmengen-Pruefung, keine Gleichheitspruefung. Doc43b
fuehrt `assistant_home` als eigenen Wert, den aktuell kein Code-Pfad erzeugt
(separat als offene Luecke geflaggt, nicht Teil des SP3-D-Auftrags) - das ist
hier bewusst kein Fehler."""
from __future__ import annotations

from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_eligibility_helpers import (
    infer_tool_target_scopes,
    target_scope_from_contract,
)
from core.routing_frame.contracts import OperationContract
from tests.operation_contract_context import canonical_contract_context

# Muss 1:1 der Liste in docs/routing/43b-capability-manifest-taxonomy.md
# ("Target Scope") entsprechen - bei Aenderung dort auch hier nachziehen.
_DOC43B_TARGET_SCOPES = {
    "assistant_identity",
    "assistant_home",
    "tool_capability",
    "runtime_state",
    "project_docs",
    "external_world",
    "time_reference",
}


def _contract(domain: str) -> OperationContract:
    raw = canonical_contract_context(
        domain=domain, primary_operation="read", target="",
        allowed_operations=("read",), scope_lock="",
    )["routing_frame"]["operation_contract"]
    contract = OperationContract.from_dict(raw)
    assert contract is not None
    return contract


def test_target_scope_from_contract_values_are_in_doc43b_taxonomy():
    for domain in ("memory", "container_runtime", "tools", "files", "time", "unknown_domain"):
        contract = _contract(domain)
        scope = target_scope_from_contract(
            domain=domain, intent_kind="", contract=contract
        )
        if scope:
            assert scope in _DOC43B_TARGET_SCOPES, scope

    capability_scope = target_scope_from_contract(
        domain="anything_else", intent_kind="capability_question", contract=_contract("anything_else")
    )
    assert capability_scope in _DOC43B_TARGET_SCOPES


def test_infer_tool_target_scopes_values_are_in_doc43b_taxonomy():
    tools = [
        ToolDescriptor(name="memory_search", capability_domain="memory", capability_operation="search"),
        ToolDescriptor(name="workspace_note", capability_domain="memory", capability_operation="read"),
        ToolDescriptor(name="container_list", capability_domain="container_runtime", capability_operation="list"),
        ToolDescriptor(name="time_now", capability_domain="time", capability_operation="read"),
        ToolDescriptor(name="file_read", capability_domain="files", capability_operation="read"),
        ToolDescriptor(name="weather_lookup", capability_domain="weather", capability_operation="read"),
    ]
    for tool in tools:
        for scope in infer_tool_target_scopes(tool):
            assert scope in _DOC43B_TARGET_SCOPES, scope
