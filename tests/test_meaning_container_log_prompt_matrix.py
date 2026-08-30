"""P11 bilingual text-to-TMR-to-OperationContract target matrix."""
from __future__ import annotations

from collections import Counter

import pytest

from core.classifier.live_claims import detect_live_claim_kind
from core.routing_frame.builder.operation_contract import build_operation_contract
from core.routing_frame.meaning import build_meaning_representation
from tests.p11_container_prompt_matrix import POSITIVE_CASES, PromptCase, render_prompt


_CONTAINER_ID = "d4f8a6c2e1b9473098fedcba76543210d4f8a6c2e1b9473098fedcba76543210"
_CONTAINER_NAME = "trion-webui"
_HEX_63 = "a" * 63
_HEX_65 = "a" * 65


def _contract_for(text: str):
    meaning = build_meaning_representation(text)
    contract = build_operation_contract(
        domain="container_runtime",
        live_claim=detect_live_claim_kind(text),
        intent_kind="action_request",
        evidence_need="live_runtime",
        meaning=meaning,
    )
    return meaning, contract


def test_prompt_matrix_has_the_authorized_language_and_target_shape():
    assert len(POSITIVE_CASES) == 32
    assert len({case.case_id for case in POSITIVE_CASES}) == 32
    assert Counter(case.language for case in POSITIVE_CASES) == {"de": 16, "en": 16}
    assert Counter((case.language, case.target_kind) for case in POSITIVE_CASES) == {
        ("de", "id"): 12,
        ("de", "name"): 4,
        ("en", "id"): 12,
        ("en", "name"): 4,
    }


@pytest.mark.parametrize("case", POSITIVE_CASES, ids=lambda case: case.case_id)
def test_bilingual_list_logs_prompts_bind_explicit_target(case: PromptCase):
    prompt, target = render_prompt(
        case,
        container_id=_CONTAINER_ID,
        container_name=_CONTAINER_NAME,
    )
    meaning, contract = _contract_for(prompt)

    assert meaning.composite_followup is not None
    assert meaning.composite_followup.semantic_sequence == ("runtime_state", "log_state")
    assert meaning.target_candidates == (target,)
    assert contract.primary_operation == "list"
    assert contract.allowed_operations == ("list",)
    assert contract.allowed_transitions == ("list->logs",)
    assert contract.target == target
    assert contract.targets == (target,)


@pytest.mark.parametrize(
    "prompt",
    (
        "Welche Container laufen? Zeige danach die Logs von abc.worker.",
        "Which containers are running? Then show logs from abc.worker.",
    ),
)
def test_dotted_container_name_with_hex_first_label_remains_bindable(prompt: str):
    meaning, contract = _contract_for(prompt)

    assert meaning.target_candidates == ("abc.worker",)
    assert contract.target == "abc.worker"
    assert contract.targets == ("abc.worker",)


@pytest.mark.parametrize(
    "prompt",
    (
        f"Welche Container laufen? Zeige danach die Logs von {_CONTAINER_ID}.worker.",
        f"Which containers are running? Then show logs from {_CONTAINER_ID}.worker.",
    ),
)
def test_dotted_container_name_with_full_id_first_label_is_not_truncated(prompt: str):
    target = f"{_CONTAINER_ID}.worker"
    meaning, contract = _contract_for(prompt)

    assert meaning.target_candidates == (target,)
    assert contract.target == target
    assert contract.targets == (target,)


@pytest.mark.parametrize(
    "prompt",
    (
        f"Die Prüfsumme ist {_CONTAINER_ID}.",
        f"The checksum is {_CONTAINER_ID}.",
        "Welche Container laufen und zeige mir die Logs von 0c67fcabd803.",
        "Which containers are running? Show logs from 0c67fcabd803.",
        "Welche Container laufen und zeige mir die Logs von abcdef123456.",
        f"Welche Container laufen und zeige mir die Logs von {_HEX_63}.",
        f"Which containers are running? Show logs from {_HEX_65}.",
        "Welche Container laufen und zeige mir die Logs.",
        "Which containers are running? Then show the logs.",
        "Welche Container laufen? Zeige danach die Logs des Containers mit der ID.",
        "Welche Container laufen? Zeige danach die Logs für den Container.",
        "Which containers are running? Show the logs for the container with ID.",
        "Which containers are running? Show the logs of the container named.",
    ),
)
def test_unbound_or_short_targets_remain_targetless(prompt: str):
    meaning, contract = _contract_for(prompt)

    assert meaning.target_candidates == ()
    assert contract.target == ""
    assert contract.targets == ()
