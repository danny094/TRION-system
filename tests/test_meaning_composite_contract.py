"""SP8-Z5a: typed composite meaning contract to OperationContract."""

from __future__ import annotations

from core.classifier.live_claims import detect_live_claim_kind
from core.routing_frame.builder.operation_contract import build_operation_contract
from core.routing_frame.contracts import OperationContract
from core.routing_frame.meaning import build_meaning_representation


_CONTAINER_ID = "d4f8a6c2e1b9473098fedcba76543210d4f8a6c2e1b9473098fedcba76543210"


def _contract_for(text: str) -> OperationContract:
    meaning = build_meaning_representation(text)
    return build_operation_contract(
        domain="container_runtime",
        live_claim=detect_live_claim_kind(text),
        intent_kind="action_request",
        evidence_need="live_runtime",
        meaning=meaning,
    )


def test_exact_structured_composite_followup_yields_transition():
    meaning = build_meaning_representation("Welche Container laufen und zeige mir die Logs.")
    assert meaning.composite_followup is not None
    assert meaning.composite_followup.semantic_sequence == ("runtime_state", "log_state")
    assert meaning.composite_followup.intent_sequence == ("list", "logs")

    contract = _contract_for("Welche Container laufen und zeige mir die Logs.")
    assert contract.primary_operation == "list"
    assert contract.allowed_operations == ("list",)
    assert contract.allowed_transitions == ("list->logs",)


def test_logzeilen_composite_token_yields_list_to_logs_transition():
    prompt = "Welche Container laufen und zeige mir die Logzeilen."
    meaning = build_meaning_representation(prompt)
    assert meaning.composite_followup is not None
    assert meaning.composite_followup.semantic_sequence == ("runtime_state", "log_state")

    contract = _contract_for(prompt)
    assert contract.primary_operation == "list"
    assert contract.allowed_operations == ("list",)
    assert contract.allowed_transitions == ("list->logs",)


def test_two_predicates_without_rule_remain_fail_closed():
    contract = _contract_for("Stoppe den Container trion-home und zeige mir die Logs.")
    assert contract.primary_operation == ""
    assert contract.allowed_operations == ()
    assert contract.allowed_transitions == ()


def test_reversed_predicate_order_does_not_create_followup():
    meaning = build_meaning_representation("Zeige mir die Logs und welche Container laufen.")
    assert meaning.composite_followup is None

    contract = _contract_for("Zeige mir die Logs und welche Container laufen.")
    assert contract.primary_operation == ""
    assert contract.allowed_transitions == ()


def test_plain_list_question_keeps_empty_transitions():
    contract = _contract_for("Welche Container laufen?")
    assert contract.primary_operation == "list"
    assert contract.allowed_operations == ("list",)
    assert contract.allowed_transitions == ()


def test_runtime_container_id_projects_to_meaning_and_operation_contract():
    prompt = f"Welche Container laufen und zeige mir anschließend die Logzeilen von {_CONTAINER_ID}."
    meaning = build_meaning_representation(prompt)
    contract = _contract_for(prompt)

    assert meaning.target_candidates == (_CONTAINER_ID,)
    assert contract.target == _CONTAINER_ID
    assert contract.targets == (_CONTAINER_ID,)


def test_runtime_container_name_projects_to_meaning_and_operation_contract():
    prompt = "Welche Container laufen und zeige mir die Logs des Containers trion-webui."
    meaning = build_meaning_representation(prompt)
    contract = _contract_for(prompt)

    assert meaning.target_candidates == ("trion-webui",)
    assert contract.target == "trion-webui"
    assert contract.targets == ("trion-webui",)


def test_unrelated_sha256_text_does_not_project_a_target():
    prompt = f"Der SHA-256-Wert {_CONTAINER_ID} wurde in der Dokumentation erwaehnt."
    meaning = build_meaning_representation(prompt)
    contract = _contract_for(prompt)

    assert meaning.target_candidates == ()
    assert contract.target == ""
    assert contract.targets == ()
