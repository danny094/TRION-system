"""Deterministischer OperationContract-Fingerprint — P11 SP2 (Doc 56).

Derselbe Contract-Inhalt erzeugt denselben Fingerprint, unabhaengig davon,
welches Downstream-Modul ihn berechnet (Plan SP2 Test: "Contract-Fingerprint
bleibt durch Orchestrator und Thinking identisch"). `provenance` wird bewusst
ausgeschlossen: Confidence/Span-Rauschen darf den Fingerprint nicht aendern —
nur der operative Vertragsinhalt zaehlt.

Eigene Datei statt Methode auf OperationContract (Doc07 "Ein-Aufgabe-pro-
Datei"): Fingerprint-Berechnung ist eine eigenstaendige, wiederverwendbare
Aufgabe, kein Teil der Contract-Definition selbst.
"""
from __future__ import annotations

import hashlib

from core.routing_frame.contracts import OperationContract


def compute_operation_contract_fingerprint(contract: OperationContract) -> str:
    """Liefert einen stabilen SHA-256-Hex-Fingerprint des Contract-Inhalts."""

    canonical = (
        contract.domain,
        contract.primary_operation,
        contract.target,
        tuple(contract.detail_fields),
        contract.mutating_action,
        tuple(contract.required_evidence),
        tuple(contract.allowed_operations),
        tuple(contract.allowed_transitions),
        contract.scope_lock,
    )
    return hashlib.sha256(repr(canonical).encode("utf-8")).hexdigest()
