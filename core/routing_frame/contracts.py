from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.classifier.contracts import ClassifierResult
from core.classifier.live_claims import LiveClaimKind
from core.dialogue_signal.contracts import DialogueSignal


@dataclass(frozen=True)
class FieldProvenance:
    """Herkunft und Konfidenz eines einzelnen MeaningRepresentation-Felds.

    Doc 55 Signalregeln: "Jedes Feld besitzt Quelle, Konfidenz und optional
    die Textspanne." `span` ist der unterstuetzende Rohtext-Ausschnitt, falls
    vorhanden — kein freier Userdaten-Dump, nur das kurze Belegfragment.
    """

    source: str
    confidence: float
    span: str = ""


@dataclass(frozen=True)
class CompositeFollowupIntent:
    """Explicit ordered composite meaning from canonical TMR rule data.

    Carries semantic predicates and their semantic intent sequence only. It
    never stores tool names, targets, arguments, evidence, user text, spans, or
    runtime artifacts.
    """

    semantic_sequence: Tuple[str, ...]
    intent_sequence: Tuple[str, ...]


@dataclass(frozen=True)
class MeaningRepresentation:
    """TRION Meaning Representation (TMR) — Doc 55.

    Normalisiert die Bedeutung einer Nutzeranfrage vor Routing/Operationswahl.
    Nur occurrence-genau kartierte, vollstaendig provenance-gebundene Paare
    duerfen ueber den einzigen R5-Projektionsowner Routing-Signale setzen.
    Enthaelt bewusst keinen Toolnamen und keine erlaubte Operation.

    Feldnamen und -reihenfolge sind gemaess P11-Plan bindend ("Zielcontracts").
    """

    speech_act: str
    predicate: str
    theme: str
    roles: Dict[str, Tuple[str, ...]]
    scope_candidates: Tuple[str, ...]
    target_candidates: Tuple[str, ...]
    requested_details: Tuple[str, ...]
    temporal: str
    polarity: str
    modality: str
    cardinality: str
    mutation_candidate: bool
    ambiguity: Tuple[str, ...]
    confidence: float
    provenance: Dict[str, FieldProvenance]
    composite_followup: Optional[CompositeFollowupIntent] = None


@dataclass(frozen=True)
class RawSignals:
    """Rohsignale vor der Frame-Normalisierung.

    Wird von collect_raw_signals() befüllt und von build_routing_frame()
    konsumiert. Kein Downstream-Modul liest RawSignals direkt.
    """

    classifier: ClassifierResult
    live_claim: LiveClaimKind
    dialogue_signal: DialogueSignal
    loop_markers: bool
    repeat_count: int
    home_scope_verified: bool
    self_context_present: bool
    # P11 SP8 R5: Der Builder darf `meaning` genau einmal durch den
    # datengetriebenen Projektionsowner lesen. Nicht kartierte, mehrdeutige
    # oder unzureichend belegte Bedeutungen bleiben ausschliesslich im
    # sanitisierten meaning_shadow_trace.
    meaning: Optional[MeaningRepresentation] = None


@dataclass(frozen=True)
class OperationTransition:
    """Typed successor operation and its contract-owned evidence need."""

    source_operation: str
    target_operation: str
    required_evidence: Tuple[str, ...]

    def __post_init__(self) -> None:
        operations = (self.source_operation, self.target_operation)
        if any(type(value) is not str or not value or value != value.strip() for value in operations):
            raise ValueError("operation_transition_invalid_operation")
        if type(self.required_evidence) is not tuple or any(
            type(value) is not str or not value or value != value.strip() for value in self.required_evidence
        ):
            raise ValueError("operation_transition_invalid_evidence")

    @property
    def edge(self) -> str:
        return f"{self.source_operation}->{self.target_operation}"


@dataclass(frozen=True)
class OperationContract:
    """TRION Operation Contract — Doc 56.

    Einzige Operations-/Scope-Wahrheit downstream (Plan-A3). Wird einmal aus
    normalisiertem RoutingFrame plus TMR gebaut (core/routing_frame/builder/
    operation_contract.py); kein Downstream-Modul berechnet Operation,
    Target, Details, Scope oder Mutation erneut aus `user_text` (Doc 56
    Signal-Provenienz-Regel).

    Feldnamen und -reihenfolge sind gemaess P11-Plan bindend ("Zielcontracts").

    Pflichtinvarianten (Doc 56):
    - `primary_operation in allowed_operations` (oder beide leer = unvollstaendig),
    - Mutationen brauchen explizites semantisches Signal (TMR `mutation_candidate`
      ohne `polarity == "negative"`),
    - ein Target allein erzeugt niemals `inspect`,
    - fehlende notwendige Werte machen den Contract unvollstaendig statt kreativ.
    """

    domain: str
    primary_operation: str
    target: str
    targets: Tuple[str, ...]
    detail_fields: Tuple[str, ...]
    mutating_action: bool
    required_evidence: Tuple[str, ...]
    allowed_operations: Tuple[str, ...]
    allowed_transitions: Tuple[str, ...]
    transition_requirements: Tuple[OperationTransition, ...]
    scope_lock: str
    provenance: Dict[str, FieldProvenance]

    def __post_init__(self) -> None:
        projected_target = self.targets[0] if self.targets else ""
        if self.target != projected_target:
            raise ValueError("operation_contract_target_projection_mismatch")
        if type(self.transition_requirements) is not tuple or any(
            type(item) is not OperationTransition for item in self.transition_requirements
        ):
            raise ValueError("operation_contract_transition_type_invalid")
        projected_edges = tuple(item.edge for item in self.transition_requirements)
        if self.allowed_transitions != projected_edges or len(set(projected_edges)) != len(projected_edges):
            raise ValueError("operation_contract_transition_projection_mismatch")

    @classmethod
    def from_dict(cls, value: Any) -> Optional["OperationContract"]:
        """Parse persisted contract data through the canonical schema owner."""
        from core.routing_frame.operation_contract_schema import parse_operation_contract

        return parse_operation_contract(value)


def _empty_operation_contract() -> "OperationContract":
    """Unvollstaendiger Contract — Default, solange kein Signal trifft."""

    return OperationContract(
        domain="",
        primary_operation="",
        target="",
        targets=(),
        detail_fields=(),
        mutating_action=False,
        required_evidence=(),
        allowed_operations=(),
        allowed_transitions=(),
        transition_requirements=(),
        scope_lock="",
        provenance={},
    )


@dataclass(frozen=True)
class RoutingFrame:
    intent_kind: str
    domain: str
    evidence_need: str
    execution_mode: str
    dialogue_style: str
    confidence: float
    requested_operation_family: str = ""  # User-Intent-Perspektive (P10 NEU)
    # P11 SP2 (Doc56 A3): operation_contract ist die einzige Operations-/
    # Scope-Wahrheit downstream. requested_operation_family oben ist nur
    # noch Projektion von operation_contract.primary_operation (Aufgabe 4).
    operation_contract: OperationContract = field(default_factory=_empty_operation_contract)
    operation_contract_fingerprint: str = ""
    source_signals: Dict[str, Any] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
