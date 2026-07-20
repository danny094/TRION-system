"""Sanitisierter Shadow-Trace fuer TMR — P11 SP1 (Doc 55 A10 / Plan SP1).

`sanitize_meaning_for_shadow_trace()` wandelt ein MeaningRepresentation in
eine reine Diagnosestruktur (JSON-faehige Primitive). Kein Konsument liest
diese Struktur in SP1 — sie wird von keinem Routing-/Toolwahl-Pfad und
keinem realen Doc-10-Event gelesen (das Verdrahten in echte Events ist
SP7, siehe P11-Plan; A11: bestehender Event-Contract bleibt fuehrend).

Sanitisierung: es wird ausschliesslich aus den TMR-Feldern selbst gebaut.
MeaningRepresentation enthaelt keinen rohen Volltext-User-Input — nur
kurze, an die kuratierten Regel-Token gebundene `span`-Fragmente
(Doc55 Signalregeln). Es wird kein zusaetzlicher Freitext angehaengt.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.routing_frame.contracts import FieldProvenance, MeaningRepresentation

_UNAVAILABLE: Dict[str, Any] = {"status": "unavailable"}


def _provenance_to_dict(prov: FieldProvenance) -> Dict[str, Any]:
    return {"source": prov.source, "confidence": prov.confidence, "span": prov.span}


def sanitize_meaning_for_shadow_trace(
    meaning: Optional[MeaningRepresentation],
) -> Dict[str, Any]:
    """Liefert eine sanitisierte, JSON-faehige Diagnosestruktur.

    Bei meaning=None (z.B. weil der TMR-Aufbau fehlschlug, siehe
    signal_collector._build_meaning_signal_safely) wird ein fester
    Platzhalter zurueckgegeben statt eines Fehlers.
    """

    if meaning is None:
        return dict(_UNAVAILABLE)

    return {
        "status": "ok",
        "speech_act": meaning.speech_act,
        "predicate": meaning.predicate,
        "theme": meaning.theme,
        "roles": {k: list(v) for k, v in meaning.roles.items()},
        "scope_candidates": list(meaning.scope_candidates),
        "target_candidates": list(meaning.target_candidates),
        "requested_details": list(meaning.requested_details),
        "temporal": meaning.temporal,
        "polarity": meaning.polarity,
        "modality": meaning.modality,
        "cardinality": meaning.cardinality,
        "mutation_candidate": meaning.mutation_candidate,
        "ambiguity": list(meaning.ambiguity),
        "confidence": meaning.confidence,
        "provenance": {
            field: _provenance_to_dict(prov) for field, prov in meaning.provenance.items()
        },
    }
