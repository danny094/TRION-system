"""T_eligible (Doc56, Mini-Savepoint B): isolierte Tests fuer
eligible_tools_for_contract() - bewusst BEVOR core/orchestrator/tools.py sie
verdrahtet (Danny, 2026-06-27: "Claude soll erst die Funktion isoliert
testen, dann erst in select_relevant_tools() verdrahten. Sonst wird es
wieder schwer zu sehen, wo genau ein Drift entsteht.").

Kein Import aus tools.py oder einer anderen Testdatei - reine Funktion
gegen ToolDescriptor/Contract-Dict, keine routing_frame-/user_text-
Abhaengigkeit.
"""
from __future__ import annotations

from core.classifier.contracts import ClassifierResult, Category, Route, SafetyLevel
from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_eligibility import eligible_tools_for_contract
from core.routing_frame.builder import build_routing_frame
from tests.operation_contract_context import canonical_contract_context


def _list_contract(**overrides) -> dict:
    contract = canonical_contract_context(
        target="trion-home", required_evidence=("runtime_status",), scope_lock="home",
    )["routing_frame"]["operation_contract"]
    contract.update(overrides)
    return contract


def _list_tool(**overrides) -> ToolDescriptor:
    fields = {
        "name": "container_list",
        "capability_domain": "container_runtime",
        "capability_operation": "list",
        "capability_entity_types": ["container"],
        "capability_evidence_types": ["runtime_status"],
        "capability_target_scopes": ["runtime_state"],
        "capability_risk": "read_only",
    }
    fields.update(overrides)
    return ToolDescriptor(**fields)


def test_matching_contract_and_tool_is_eligible():
    eligible = eligible_tools_for_contract([_list_tool()], _list_contract())
    assert [tool.name for tool in eligible] == ["container_list"]


def test_wrong_operation_excludes_tool():
    tool = _list_tool(capability_operation="inspect")
    assert eligible_tools_for_contract([tool], _list_contract()) == []


def test_missing_evidence_excludes_tool():
    tool = _list_tool(capability_evidence_types=["runtime_inventory"])
    assert eligible_tools_for_contract([tool], _list_contract()) == []


def test_scope_mismatch_excludes_tool():
    # memory-Tool gegen einen container_runtime-Contract: target_scope
    # ("runtime_state") liegt nicht in den expliziten Tool-Target-Scopes.
    tool = ToolDescriptor(
        name="memory_search",
        capability_domain="container_runtime",
        capability_operation="list",
        capability_evidence_types=["runtime_status"],
        capability_target_scopes=["assistant_identity"],
        capability_risk="read_only",
    )
    assert eligible_tools_for_contract([tool], _list_contract()) == []


def test_mutating_action_false_blocks_risky_tool():
    risky_tool = _list_tool(name="container_restart", capability_operation="execute", capability_risk="mutating")
    contract = _list_contract(primary_operation="execute", allowed_operations=["execute"], mutating_action=False, required_evidence=[])
    assert eligible_tools_for_contract([risky_tool], contract) == []


def test_mutating_action_true_permits_matching_risky_tool():
    risky_tool = _list_tool(name="container_restart", capability_operation="execute", capability_risk="mutating")
    contract = _list_contract(primary_operation="execute", allowed_operations=["execute"], mutating_action=True, required_evidence=[])
    eligible = eligible_tools_for_contract([risky_tool], contract)
    assert [tool.name for tool in eligible] == ["container_restart"]


def test_mutating_contract_requires_explicit_tool_domain_and_operation():
    """Sicherheitsrelevant: ein Tool ohne explizite capability_domain/
    capability_operation (nur ueber Heuristik aus Name/Beschreibung
    inferierbar) wird fuer einen mutierenden Contract NICHT freigegeben -
    auch wenn infer_tool_domain()/infer_tool_operation_family() denselben
    Wert heuristisch liefern wuerden."""
    heuristic_tool = ToolDescriptor(
        name="container_runtime_start_tool",
        description="start a container",
        capability_evidence_types=["runtime_state_change"],
        capability_risk="mutating",
    )
    contract = _list_contract(primary_operation="execute", allowed_operations=["execute"], mutating_action=True, required_evidence=[])
    assert eligible_tools_for_contract([heuristic_tool], contract) == []


def test_non_mutating_contract_requires_explicit_tool_domain_and_operation():
    """Codex SP3-D-Fund (2026-06-28): Doc56 ("Fehlt ein Pflichtfeld, ist das
    Tool nicht direkt vertragsfaehig; Keyword-Fallback darf es nicht
    freigeben") gilt fuer ALLE Contracts, nicht nur fuer mutierende. Ein Tool
    ohne explizite capability_domain/capability_operation (nur ueber
    Heuristik aus Name/Beschreibung inferierbar) wird auch fuer einen
    nicht-mutierenden Contract NICHT freigegeben - auch wenn
    infer_tool_domain()/infer_tool_operation_family() denselben Wert
    heuristisch liefern wuerden (Repro: name="container_list",
    description="List containers" haette ohne diesen Fix ueber den
    Keyword-Pfad domain="container_runtime"/operation="list" erraten)."""
    heuristic_tool = ToolDescriptor(
        name="container_list",
        description="List containers",
        capability_evidence_types=["runtime_status"],
        capability_risk="read_only",
    )
    assert eligible_tools_for_contract([heuristic_tool], _list_contract()) == []


def test_required_args_missing_does_not_affect_eligibility():
    """Doc56: T_eligible prueft Domain/Operation/Evidence/Scope/Risiko -
    Pflichtargumente (required_args) gehoeren zu T_executable_now, nicht zu
    T_eligible. Ein Tool mit unbound required_args bleibt eligible."""
    tool = _list_tool(capability_required_args=["container_id_or_name"])
    eligible = eligible_tools_for_contract([tool], _list_contract())
    assert [t.name for t in eligible] == ["container_list"]


def test_empty_contract_dict_yields_no_tools():
    assert eligible_tools_for_contract([_list_tool()], {}) == []


def test_none_contract_yields_no_tools():
    assert eligible_tools_for_contract([_list_tool()], None) == []


def test_incomplete_contract_yields_no_tools():
    contract = _list_contract(primary_operation="")
    assert eligible_tools_for_contract([_list_tool()], contract) == []


def test_missing_allowed_operations_blocks():
    """Codex P1 (2026-06-28): fehlendes allowed_operations darf nicht stillschweigend
    auf [primary_operation] repariert werden - fail-closed statt Annahme."""
    contract = _list_contract()
    del contract["allowed_operations"]
    assert eligible_tools_for_contract([_list_tool()], contract) == []


def test_empty_allowed_operations_blocks():
    contract = _list_contract(allowed_operations=[])
    assert eligible_tools_for_contract([_list_tool()], contract) == []


def test_primary_operation_not_in_allowed_operations_blocks():
    contract = _list_contract(allowed_operations=["inspect"])
    assert eligible_tools_for_contract([_list_tool()], contract) == []


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


def test_execute_contract_has_no_evidence_sentinel_and_gates_via_explicit_tool_contract():
    """Danny-Regression (2026-06-27) nach Fund des Evidence-Sentinels
    'manifestdefiniert': der reale Contract-Builder darf diesen Platzhalter
    nicht mehr in required_evidence liefern, und die Eligibility fuer das
    mutierende Tool laeuft ausschliesslich ueber das explizite Tool-Contract
    (Domain+Operation+Risk), nicht ueber eine Evidence-Pruefung."""
    frame = build_routing_frame("Starte den Container trion-home.", _classifier())
    contract = frame["operation_contract"]
    assert contract["primary_operation"] == "execute"
    assert contract["mutating_action"] is True
    assert tuple(contract["required_evidence"]) == ()
    assert "manifestdefiniert" not in contract["required_evidence"]

    explicit_tool = ToolDescriptor(
        name="request_container",
        capability_domain="container_runtime",
        capability_operation="start",
        capability_evidence_types=["runtime_state_change"],
        capability_target_scopes=["runtime_state"],
        capability_risk="mutating",
    )
    eligible = eligible_tools_for_contract([explicit_tool], contract)
    assert [tool.name for tool in eligible] == ["request_container"]
