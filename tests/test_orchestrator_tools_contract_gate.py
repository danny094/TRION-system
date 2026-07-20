"""P11 SP2 Codex-P1-Fix: Fallback ohne Contract gibt keine Tools frei.

Plan-Stop (p11-meaning-operation-contract.md, SP2): "Kein produktiver Pfad
darf parallel eine zweite Operation berechnen." Aufgabe 6: "Fallback ohne
Contract darf keine Tools freigeben."

Befund (Codex-Review): core/orchestrator/tools.py::select_relevant_tools()
rief vor dem Fix einen Rohtext-Resolver unabhaengig vom OperationContract auf.
Bei unvollstaendigem Contract (primary_operation == "") konnte der alte
Rohtext-Pfad trotzdem ein Tool freigeben — mechanisch reproduziert mit
"Pruefe den Container trion-home." (Contract leer, da kein eindeutiges
Praedikat/Detail; der alte Rohtextpfad leitete dennoch operation="inspect" ab).

Bewusst kein Import aus einer anderen Testdatei — eigener lokaler Helper.
Touched test_orchestrator_tools.py wurde NICHT erweitert (bereits 277
Zeilen vor dieser Aenderung, Doc07-Cap ohne Grandfathering haette ein
Anfassen sofort blockiert) — daher eigene Datei.
"""
from __future__ import annotations

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tools import select_relevant_tools
from core.routing_frame.builder import build_routing_frame


def _classifier() -> ClassifierResult:
    return ClassifierResult(
        category=Category.TOOL,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=True,
        confidence=0.9,
        route=Route.NEEDS_ORCHESTRATOR,
        matched_pattern="test",
        reason="test",
    )


def _inspect_tool() -> ToolDescriptor:
    return ToolDescriptor(
        name="container_inspect",
        capability_domain="container_runtime",
        capability_operation="inspect",
        capability_entity_types=["container"],
        capability_evidence_types=["runtime_metadata", "home_scope"],
        capability_target_scopes=["runtime_state"],
        capability_required_args=["container_id_or_name"],
        capability_risk="read_only",
    )


def test_incomplete_contract_blocks_rawtext_spec_fallback_inspect_tool():
    """Bare Target ohne Praedikat -> Contract bleibt leer (Doc56 Pflicht-
    invariante 'Ein Target allein erzeugt niemals inspect'). Der alte
    Rohtext-Spec-Resolver wuerde 'inspect' liefern (mentions 'prüfe') und das
    passende Tool freigeben — das ist exakt der per Plan-Stop verbotene
    zweite Operationspfad."""
    text = "Pruefe den Container trion-home."
    frame = build_routing_frame(text, _classifier())
    assert frame["operation_contract"]["primary_operation"] == ""

    selected = select_relevant_tools(text, _classifier(), [_inspect_tool()], routing_frame=frame)
    assert selected == []


def test_complete_contract_still_permits_tool_selection():
    """Gegenprobe: ein vollstaendiger Contract (Statusfrage -> list) darf
    weiterhin Tools freigeben — der Fix darf den Erfolgsfall nicht brechen."""
    text = "Laeuft der Container trion-home?"
    frame = build_routing_frame(text, _classifier())
    assert frame["operation_contract"]["primary_operation"] == "list"

    list_tool = ToolDescriptor(
        name="container_list",
        capability_domain="container_runtime",
        capability_operation="list",
        capability_entity_types=["container"],
        capability_evidence_types=["runtime_status"],
        capability_target_scopes=["runtime_state"],
        capability_risk="read_only",
    )
    selected = select_relevant_tools(text, _classifier(), [list_tool], routing_frame=frame)
    assert [tool.name for tool in selected] == ["container_list"]


def test_missing_operation_contract_key_fails_closed():
    """SP3-P DECIDE B: ohne OperationContract keine Toolauswahl."""
    text = "Pruefe den Container trion-home."
    selected = select_relevant_tools(text, _classifier(), [_inspect_tool()], routing_frame=None)
    assert selected == []
