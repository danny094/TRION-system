"""P11 SP2 (Doc 56): Negation/Mutation/Modalitaet/Composite/Mehrdeutigkeit.

Ausgelagert aus test_operation_contract.py (Doc07 200-Zeilen-Cap). Bewusst
kein Import aus einer anderen Testdatei — eigener lokaler Helper, eigene
Datei ist die einzige Wahrheit fuer diese Tests.

Plan SP2 Tests: "Negation, Modalitaet, Mutation, Composite Requests und
Mehrdeutigkeit" sowie die Pflichtinvariante
`primary_operation in allowed_operations` (oder beide leer).
"""
from __future__ import annotations

from core.classifier.live_claims import detect_live_claim_kind
from core.routing_frame.builder.operation_contract import build_operation_contract
from core.routing_frame.contracts import OperationContract
from core.routing_frame.meaning import build_meaning_representation


def _contract_for(text: str) -> OperationContract:
    meaning = build_meaning_representation(text)
    live_claim = detect_live_claim_kind(text)
    return build_operation_contract(
        domain="container_runtime",
        live_claim=live_claim,
        intent_kind="action_request",
        evidence_need="live_runtime",
        meaning=meaning,
    )


# ---------------------------------------------------------------------------
# Negation: Mutation ohne explizites Freigabesignal bleibt unvollstaendig
# (meaning_modifier_tokens.csv: nicht -> polarity=negative)
# ---------------------------------------------------------------------------


def test_negated_mutation_does_not_yield_execute():
    contract = _contract_for("Stoppe den Container trion-home nicht.")
    assert contract.primary_operation == ""
    assert contract.mutating_action is False
    assert contract.allowed_operations == ()


# ---------------------------------------------------------------------------
# Mutation: unambiguer, nicht negierter Lifecycle-Request -> execute
# ---------------------------------------------------------------------------


def test_clean_mutation_request_yields_execute():
    contract = _contract_for("Starte den Container trion-home.")
    assert contract.primary_operation == "execute"
    assert contract.mutating_action is True
    assert contract.allowed_operations == ("execute",)
    # Danny-Entscheidung 2026-06-27: kein Evidence-Sentinel mehr - execute
    # hat keinen fixen kanonischen Evidence-Typ, das Tool-Contract-Gate
    # (Domain+Operation+Risk) entscheidet stattdessen ueber Eligibility.
    assert contract.required_evidence == ()


# ---------------------------------------------------------------------------
# Modalitaet: modale Formulierung aendert die Operation nicht
# (meaning_modifier_tokens.csv: can -> modality=can)
# ---------------------------------------------------------------------------


def test_modality_does_not_change_list_operation():
    contract = _contract_for("Can you check if the container trion-home is running?")
    assert contract.primary_operation == "list"
    assert contract.target == "trion-home"


def test_modality_does_not_block_clean_mutation():
    contract = _contract_for("Can you stop the container trion-home?")
    assert contract.primary_operation == "execute"
    assert contract.mutating_action is True


# ---------------------------------------------------------------------------
# Composite Requests / Mehrdeutigkeit: zwei distinkte Praedikat-Treffer
# -> ambiguous (TMR-Confidence 0.5) -> Contract bleibt unvollstaendig statt
# eine der beiden Operationen zu erraten (Stop-Bedingung SP2).
# ---------------------------------------------------------------------------


def test_composite_request_with_two_predicates_yields_incomplete():
    """'stoppe' (lifecycle_action) + 'logs' (log_state) im selben Satz."""
    contract = _contract_for("Stoppe den Container trion-home und zeige mir die Logs.")
    assert contract.primary_operation == ""
    assert contract.allowed_operations == ()


def test_ambiguous_disjunction_yields_incomplete():
    """'aktiv' (runtime_state) vs. 'neustarten' (lifecycle_action) per 'oder'."""
    contract = _contract_for(
        "Ist der Container trion-home aktiv oder soll ich ihn neustarten?"
    )
    assert contract.primary_operation == ""
    assert contract.allowed_operations == ()


# ---------------------------------------------------------------------------
# Logs-Pfad (vollstaendigkeitshalber, Doc56 kanonische Operation "logs")
# ---------------------------------------------------------------------------


def test_log_predicate_yields_logs_operation():
    contract = _contract_for("Zeige mir die Logs vom Container trion-home.")
    assert contract.primary_operation == "logs"
    assert contract.required_evidence == ("runtime_logs",)


# ---------------------------------------------------------------------------
# Pflichtinvariante: primary_operation in allowed_operations (oder beide leer)
# ---------------------------------------------------------------------------


def test_primary_operation_always_in_allowed_operations_or_both_empty():
    fixtures = (
        "Welche Container laufen?",
        "Läuft der Container trion-home?",
        "Welche Ports hat der Container trion-home?",
        "Container trion-home.",
        "Stoppe den Container trion-home nicht.",
        "Starte den Container trion-home.",
        "Zeige mir die Logs vom Container trion-home.",
        "Stoppe den Container trion-home und zeige mir die Logs.",
    )
    for text in fixtures:
        contract = _contract_for(text)
        if contract.primary_operation == "":
            assert contract.allowed_operations == ()
        else:
            assert contract.primary_operation in contract.allowed_operations
