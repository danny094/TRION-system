"""P11 SP2 (Doc 56): OperationContract als einzige Operationsautoritaet.

Testet core/routing_frame/builder/operation_contract.py (Contract Builder)
direkt gegen echte TMR-Regeltabellen (intelligence_modules/cim_skill_rag/
meaning_*_tokens.csv): Signatur/Rohtext-Verbot, leere Meaning, Paraphrasen,
Target/Detail/Status. Negation/Mutation/Modalitaet/Composite/Mehrdeutigkeit/
Logs/Pflichtinvariante sind ausgelagert in
test_operation_contract_mutation.py; Fingerprint- und
build_routing_frame()-Integration in test_operation_contract_fingerprint.py
(Doc07 200-Zeilen-Cap).

Bewusst keine Mocks der TMR-Regeltabellen: jede Fixture-Phrase ist gegen die
tatsaechlichen CSV-Zeilen (meaning_concept_tokens.csv / meaning_role_tokens.csv
/ meaning_detail_tokens.csv / meaning_modifier_tokens.csv) verifiziert, siehe
Kommentare an den jeweiligen Tests.
"""
from __future__ import annotations

import inspect

from core.classifier.live_claims import LiveClaimKind, detect_live_claim_kind
from core.routing_frame.builder.operation_contract import build_operation_contract
from core.routing_frame.contracts import OperationContract
from core.routing_frame.meaning import build_meaning_representation


def _contract_for(
    text: str,
    *,
    domain: str = "container_runtime",
    intent_kind: str = "action_request",
    evidence_need: str = "live_runtime",
) -> OperationContract:
    """Baut den Contract aus echter TMR-Pipeline (kein Mock)."""

    meaning = build_meaning_representation(text)
    live_claim = detect_live_claim_kind(text)
    return build_operation_contract(
        domain=domain,
        live_claim=live_claim,
        intent_kind=intent_kind,
        evidence_need=evidence_need,
        meaning=meaning,
    )


# ---------------------------------------------------------------------------
# Aufgabe 2: kein user_text-Parameter im Contract Builder
# ---------------------------------------------------------------------------


def test_build_operation_contract_has_no_user_text_parameter():
    """Plan SP2 Aufgabe 2: 'kein user_text-Parameter'. Mechanischer Beweis
    statt Annahme: Signatur enthaelt kein user_text/text/raw_text-Feld."""
    params = set(inspect.signature(build_operation_contract).parameters)
    assert "user_text" not in params
    assert "text" not in params
    assert "raw_text" not in params
    assert params == {"domain", "live_claim", "intent_kind", "evidence_need", "meaning"}


def test_build_operation_contract_module_has_no_downstream_rawtext_helpers():
    """'kein Downstream-Rohtextzugriff fuer Operation/Target/Details': das
    Modul importiert keine alten Rohtext-Resolver (geprueft gegen die
    tatsaechlichen Import-Statements, nicht gegen Kommentartext)."""
    import ast

    import core.routing_frame.builder.operation_contract as mod

    tree = ast.parse(inspect.getsource(mod))
    imported_modules = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    ]
    assert not any("resolvers" in m for m in imported_modules)


def test_build_operation_contract_empty_meaning_yields_incomplete_contract():
    contract = build_operation_contract(
        domain="container_runtime",
        live_claim=LiveClaimKind.CONTAINER_RUNTIME,
        intent_kind="action_request",
        evidence_need="live_runtime",
        meaning=None,
    )
    assert contract.primary_operation == ""
    assert contract.allowed_operations == ()


# ---------------------------------------------------------------------------
# Drei Container-Paraphrasen -> identischer Contract "list"
# (meaning_concept_tokens.csv: laufen/läuft/aktiv -> predicate=runtime_state,
#  live_claim_tokens.csv: container/läuft -> CONTAINER_RUNTIME)
# ---------------------------------------------------------------------------


def test_three_container_paraphrases_yield_identical_list_operation():
    paraphrases = (
        "Welche Container laufen?",
        "Was läuft zuhause?",
        "Sind die Container aktiv?",
    )
    contracts = [_contract_for(text) for text in paraphrases]
    for contract in contracts:
        assert contract.primary_operation == "list"
        assert contract.allowed_operations == ("list",)
        assert contract.required_evidence == ("runtime_inventory",)
        assert contract.mutating_action is False
        assert contract.target == ""


# ---------------------------------------------------------------------------
# Target-Statusfrage -> list, Detailfrage (gleiches Target) -> inspect
# (meaning_role_tokens.csv: trion-home -> target_alias;
#  meaning_detail_tokens.csv: ports -> detail)
# ---------------------------------------------------------------------------


def test_target_status_question_yields_list_with_runtime_status_evidence():
    contract = _contract_for("Läuft der Container trion-home?")
    assert contract.primary_operation == "list"
    assert contract.target == "trion-home"
    assert contract.required_evidence == ("runtime_status",)


def test_target_detail_question_same_target_yields_inspect():
    contract = _contract_for("Welche Ports hat der Container trion-home?")
    assert contract.primary_operation == "inspect"
    assert contract.target == "trion-home"
    assert contract.detail_fields == ("ports",)
    assert contract.required_evidence == ("runtime_metadata",)


def test_bare_target_without_predicate_never_yields_inspect():
    """Doc 56 Pflichtinvariante: 'Ein Target allein erzeugt niemals inspect'.
    Ohne Praedikat/Detail bleibt der Contract unvollstaendig statt zu raten."""
    contract = _contract_for("Container trion-home.")
    assert contract.target == "trion-home"
    assert contract.primary_operation != "inspect"
    assert contract.primary_operation == ""
    assert contract.allowed_operations == ()
