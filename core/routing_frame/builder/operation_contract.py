"""OperationContract-Builder — P11 SP2 (Doc 56).

`build_operation_contract()` baut den einzigen Operations-Contract aus dem
bereits normalisierten Routing Frame (domain, live_claim, intent_kind,
evidence_need) und dem TMR-Signal (MeaningRepresentation). Bewusst kein
`user_text`-Parameter (Plan SP2 Aufgabe 2) — jedes Feld kommt aus bereits
abgeleiteten, typisierten Signalen.

Signal-Provenienz (Doc 56): Intent/Domain/Evidence-Bedarf kommen aus dem
Frame. Target/Details/Mutationshinweise kommen ausschliesslich aus TMR.
Mehrdeutige oder fehlende Signale ergeben einen unvollstaendigen Contract
(`primary_operation == ""`) statt einer erratenen Operation.
"""
from __future__ import annotations

from core.classifier.live_claims import LiveClaimKind
from core.routing_frame.contracts import (
    MeaningRepresentation,
    OperationContract,
    _empty_operation_contract,
)

_PREDICATE_AMBIGUOUS_CONFIDENCE = 0.5  # siehe meaning_signals._AMBIGUOUS_CONFIDENCE
_MUTATING_OPERATIONS = {"write", "update", "delete", "execute", "maintain"}


def build_operation_contract(
    *,
    domain: str,
    live_claim: LiveClaimKind,
    intent_kind: str,
    evidence_need: str,
    meaning: MeaningRepresentation | None,
) -> OperationContract:
    if meaning is None:
        return _empty_operation_contract()

    target = meaning.target_candidates[0] if meaning.target_candidates else ""
    scope_lock = meaning.scope_candidates[0] if meaning.scope_candidates else ""
    detail_fields = meaning.requested_details

    if _predicate_ambiguous(meaning) and not _has_composite_followup(meaning):
        return _incomplete(domain, target, detail_fields, scope_lock, meaning)

    if live_claim == LiveClaimKind.CONTAINER_RUNTIME:
        return _container_runtime(domain, target, detail_fields, scope_lock, meaning)
    if domain == "memory":
        return _memory(domain, target, detail_fields, scope_lock, meaning, intent_kind)
    if live_claim in (LiveClaimKind.FILE_CONTENT, LiveClaimKind.TIME, LiveClaimKind.HARDWARE):
        return _read_only(domain, target, detail_fields, scope_lock, meaning, evidence_need)
    return _incomplete(domain, target, detail_fields, scope_lock, meaning)


def _container_runtime(domain, target, detail_fields, scope_lock, meaning):
    predicate = meaning.predicate
    if predicate == "log_state":
        return _build(
            domain,
            "logs",
            target,
            detail_fields,
            scope_lock,
            meaning,
            ("runtime_logs",),
            _composite_sequence(meaning, "logs"),
        )
    if predicate == "lifecycle_action" and meaning.mutation_candidate:
        # Doc 56: Mutationen brauchen explizites semantisches Signal — eine
        # Negation ("stoppe ... nicht") ist kein Mutations-Freigabesignal.
        if meaning.polarity == "negative":
            return _incomplete(domain, target, detail_fields, scope_lock, meaning)
        # Danny-Entscheidung 2026-06-27: kein Evidence-Sentinel mehr. Fuer
        # execute gibt es keinen fixen, kanonischen Evidence-Typ (Doc56:
        # "Evidence-Namen muessen aus der kanonischen Manifest-Taxonomie
        # stammen") - die Tool-Eligibility fuer mutierende Operationen laeuft
        # stattdessen ueber das Tool-Contract-Gate in
        # core/orchestrator/tool_eligibility.py (Domain+Operation explizit, Risk
        # passend zu mutating_action), nicht ueber required_evidence.
        return _build(
            domain,
            "execute",
            target,
            detail_fields,
            scope_lock,
            meaning,
            (),
            _composite_sequence(meaning, "execute"),
        )
    if detail_fields:
        # Doc 56: ein Target allein erzeugt niemals inspect — erst konkrete
        # Detailfelder (ports/mounts) tun das.
        return _build(
            domain,
            "inspect",
            target,
            detail_fields,
            scope_lock,
            meaning,
            ("runtime_metadata",),
            _composite_sequence(meaning, "inspect"),
        )
    if predicate == "runtime_state":
        evidence = ("runtime_status",) if target else ("runtime_inventory",)
        return _build(
            domain,
            "list",
            target,
            detail_fields,
            scope_lock,
            meaning,
            evidence,
            _composite_sequence(meaning, "list"),
        )
    return _incomplete(domain, target, detail_fields, scope_lock, meaning)


def _memory(domain, target, detail_fields, scope_lock, meaning, intent_kind):
    # Kein user_text-Zugriff hier: ausschliesslich der bereits im Frame
    # normalisierte intent_kind entscheidet. Der fruehere Rohtext-Resolverpfad
    # wurde in SP3-U entfernt; T_eligible entsteht aus dem Contract.
    if intent_kind in {"capability_test", "task_loop_request"}:
        return _build(domain, "search", target, detail_fields, scope_lock, meaning, ("memory_context",), ())
    return _incomplete(domain, target, detail_fields, scope_lock, meaning)


def _read_only(domain, target, detail_fields, scope_lock, meaning, evidence_need):
    evidence = (evidence_need,) if evidence_need and evidence_need != "none" else ()
    return _build(domain, "read", target, detail_fields, scope_lock, meaning, evidence, ())


def _build(
    domain,
    operation,
    target,
    detail_fields,
    scope_lock,
    meaning,
    required_evidence,
    composite_sequence,
):
    if _predicate_ambiguous(meaning) and not composite_sequence:
        return _incomplete(domain, target, detail_fields, scope_lock, meaning)
    return OperationContract(
        domain=domain,
        primary_operation=operation,
        target=target,
        detail_fields=detail_fields,
        mutating_action=operation in _MUTATING_OPERATIONS,
        required_evidence=required_evidence,
        allowed_operations=(operation,),
        allowed_transitions=_transitions(composite_sequence),
        scope_lock=scope_lock,
        provenance=dict(meaning.provenance),
    )


def _has_composite_followup(meaning):
    return bool(getattr(meaning, "composite_followup", None))


def _predicate_ambiguous(meaning):
    predicate_prov = meaning.provenance.get("predicate")
    return bool(predicate_prov and predicate_prov.confidence == _PREDICATE_AMBIGUOUS_CONFIDENCE)


def _composite_sequence(meaning, operation):
    followup = getattr(meaning, "composite_followup", None)
    if followup is None:
        return ()
    sequence = tuple(getattr(followup, "intent_sequence", ()) or ())
    if len(sequence) < 2 or sequence[0] != operation:
        return ()
    return sequence


def _transitions(sequence):
    return tuple(f"{left}->{right}" for left, right in zip(sequence, sequence[1:]))


def _incomplete(domain, target, detail_fields, scope_lock, meaning):
    return OperationContract(
        domain=domain,
        primary_operation="",
        target=target,
        detail_fields=detail_fields,
        mutating_action=False,
        required_evidence=(),
        allowed_operations=(),
        allowed_transitions=(),
        scope_lock=scope_lock,
        provenance=dict(meaning.provenance),
    )
