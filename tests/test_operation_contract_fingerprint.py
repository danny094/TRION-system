"""P11 SP2 (Doc 56): Contract-Fingerprint + build_routing_frame()-Integration.

Ausgelagert aus test_operation_contract.py (Doc07 200-Zeilen-Cap). Bewusst
kein Import aus einer anderen Testdatei — eigener lokaler Helper, eigene
Datei ist die einzige Wahrheit fuer diese Tests.

Aufgabe 3+4 verlangen, dass der Contract unveraendert mit Fingerprint durch
build_routing_frame() gefuehrt wird und requested_operation_family nur noch
Projektion von operation_contract.primary_operation ist. Der Fingerprint-
Test beweist zusaetzlich Plan-Test "Contract-Fingerprint bleibt durch
Orchestrator und Thinking identisch": Provenance-Rauschen darf den
Fingerprint nicht aendern, nur der operative Vertragsinhalt zaehlt.
"""
from __future__ import annotations

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.classifier.live_claims import detect_live_claim_kind
from core.routing_frame.builder import build_routing_frame
from core.routing_frame.builder.contract_fingerprint import (
    compute_operation_contract_fingerprint,
)
from core.routing_frame.builder.operation_contract import build_operation_contract
from core.routing_frame.contracts import FieldProvenance, OperationContract
from core.routing_frame.meaning import build_meaning_representation


def _classifier(
    category: Category = Category.INFORMATION,
    *,
    needs_orchestrator: bool = False,
    route: Route | None = None,
) -> ClassifierResult:
    return ClassifierResult(
        category=category,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=needs_orchestrator,
        confidence=0.9,
        route=route or (Route.NEEDS_ORCHESTRATOR if needs_orchestrator else Route.DIRECT_TO_THINKING),
        matched_pattern="test",
        reason="test",
    )


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
# Contract-Fingerprint bleibt durch Orchestrator und Thinking identisch
# ---------------------------------------------------------------------------


def test_fingerprint_identical_regardless_of_provenance_noise():
    """Zwei Contracts mit identischem operativem Inhalt aber unterschied-
    licher Provenance (simuliert: einmal vom 'Orchestrator', einmal vom
    'Thinking'-Modul gelesen/neu verpackt) muessen denselben Fingerprint
    ergeben — Provenance ist Diagnose, kein Vertragsinhalt."""
    base = _contract_for("Läuft der Container trion-home?")

    reread_by_other_module = OperationContract(
        domain=base.domain,
        primary_operation=base.primary_operation,
        target=base.target,
        detail_fields=base.detail_fields,
        mutating_action=base.mutating_action,
        required_evidence=base.required_evidence,
        allowed_operations=base.allowed_operations,
        allowed_transitions=base.allowed_transitions,
        scope_lock=base.scope_lock,
        provenance={"predicate": FieldProvenance(source="thinking_replay", confidence=0.99)},
    )

    assert compute_operation_contract_fingerprint(
        base
    ) == compute_operation_contract_fingerprint(reread_by_other_module)


def test_fingerprint_differs_when_operation_differs():
    list_contract = _contract_for("Läuft der Container trion-home?")
    inspect_contract = _contract_for("Welche Ports hat der Container trion-home?")
    assert compute_operation_contract_fingerprint(
        list_contract
    ) != compute_operation_contract_fingerprint(inspect_contract)


def test_fingerprint_differs_when_allowed_transition_differs():
    plain = _contract_for("Welche Container laufen?")
    composite = _contract_for("Welche Container laufen und zeige mir die Logs.")
    assert plain.primary_operation == composite.primary_operation == "list"
    assert plain.allowed_transitions == ()
    assert composite.allowed_transitions == ("list->logs",)
    assert compute_operation_contract_fingerprint(plain) != compute_operation_contract_fingerprint(
        composite
    )


# ---------------------------------------------------------------------------
# Aufgabe 3+4 Integration: build_routing_frame() fuehrt Contract+Fingerprint
# unveraendert, requested_operation_family ist reine Projektion.
# ---------------------------------------------------------------------------


def test_routing_frame_contains_operation_contract_and_fingerprint():
    frame = build_routing_frame(
        "Starte den Container trion-home.",
        _classifier(Category.TOOL, needs_orchestrator=True),
    )
    assert frame["operation_contract"]["primary_operation"] == "execute"
    assert isinstance(frame["operation_contract_fingerprint"], str)
    assert frame["operation_contract_fingerprint"] != ""


def test_routing_frame_requested_operation_family_is_contract_projection():
    frame = build_routing_frame(
        "Starte den Container trion-home.",
        _classifier(Category.TOOL, needs_orchestrator=True),
    )
    assert frame["requested_operation_family"] == frame["operation_contract"]["primary_operation"]
    assert frame["requested_operation_family"] == "execute"


def test_routing_frame_fingerprint_matches_standalone_computation():
    """Derselbe Contract-Inhalt -> derselbe Fingerprint, egal ob im Frame
    oder direkt ueber compute_operation_contract_fingerprint() berechnet."""
    frame = build_routing_frame(
        "Welche Ports hat der Container trion-home?",
        _classifier(Category.TOOL, needs_orchestrator=True),
    )
    standalone = _contract_for("Welche Ports hat der Container trion-home?")
    assert frame["operation_contract_fingerprint"] == compute_operation_contract_fingerprint(
        standalone
    )
