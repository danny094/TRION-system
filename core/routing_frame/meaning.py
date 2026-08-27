"""TMR-Builder — P11 SP1 (Doc 55).

`build_meaning_representation(user_text)` ist ein reiner Signalproduzent:
deterministisch, regelbasiert, kein LLM-Call (Doc 55 A2), keine Operation
und kein Toolname (Doc 55 A1). Quellen sind ausschliesslich die hot-reload-
faehigen Regeltabellen aus intelligence_modules/cim_skill_rag/.

P11-SP8-R5 projiziert ausschliesslich occurrence-genau kartierte
Predicate-/Theme-Paare produktiv in Routing-Signale. Alle nicht kartierten
TMR-Felder bleiben reine, sanitierte Trace-Daten ohne Toolwahl-Autoritaet.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from core.routing_frame.composite_meaning import composite_followup_from_matches
from core.routing_frame.contracts import FieldProvenance, MeaningRepresentation
from core.routing_frame.meaning_signals import (
    collect_matches,
    collect_ordered_matches,
    contains_token,
    dedupe_preserve_order,
    default_temporal,
    pick_primary,
)
from core.routing_frame.meaning_targets import target_candidates_from_text
from intelligence_modules.cim_skill_rag.meaning_concept_loader import (
    load_meaning_concept_tokens,
)
from intelligence_modules.cim_skill_rag.meaning_detail_loader import (
    load_meaning_detail_tokens,
)
from intelligence_modules.cim_skill_rag.meaning_modifier_loader import (
    load_meaning_modifier_tokens,
)
from intelligence_modules.cim_skill_rag.meaning_role_loader import (
    load_meaning_role_tokens,
)

_CARDINALITY_ALL_TOKENS = ("alle", "all", "jede", "jeden", "every")


def _derive_speech_act(text: str, predicate: str) -> Tuple[str, FieldProvenance]:
    if "?" in text:
        return "question", FieldProvenance(source="heuristic:punctuation", confidence=0.7)
    if predicate == "lifecycle_action":
        return "request_action", FieldProvenance(source="heuristic:predicate", confidence=0.6)
    return "statement", FieldProvenance(source="heuristic:default", confidence=0.3)


def _derive_cardinality(
    lowered: str, target_candidates: Tuple[str, ...]
) -> Tuple[str, FieldProvenance]:
    for token in _CARDINALITY_ALL_TOKENS:
        if f" {token} " in f" {lowered} " or lowered.startswith(f"{token} ") or lowered == token:
            return "all", FieldProvenance(source="heuristic:cardinality_all", confidence=0.6)
    if target_candidates:
        return "one", FieldProvenance(source="heuristic:cardinality_target", confidence=0.6)
    return "unspecified", FieldProvenance(source="default_unspecified", confidence=0.3)


def _roles_from_role_rows(
    role_rows: List[Dict[str, str]], lowered: str
) -> Dict[str, Tuple[str, ...]]:
    roles: Dict[str, List[str]] = {}
    for row in role_rows:
        role_name = row.get("role", "")
        if role_name in ("scope", "target_alias") or not role_name:
            continue  # eigene Top-Level-Felder, siehe Doc55 Mindestinhalt.
        token = row.get("token", "")
        value = row.get("value", "")
        if token and value and contains_token(lowered, token):
            roles.setdefault(role_name, []).append(value)
    return {k: dedupe_preserve_order(v) for k, v in roles.items()}


def build_meaning_representation(user_text: str) -> MeaningRepresentation:
    """Baut ein MeaningRepresentation deterministisch aus Rohtext.

    Leer statt erfunden: jedes Feld ohne Regeltreffer bleibt "" / () / {}.
    """

    text = str(user_text or "")
    lowered = text.lower().strip()

    concept_rows = load_meaning_concept_tokens()
    role_rows = load_meaning_role_tokens()
    detail_rows = load_meaning_detail_tokens()
    modifier_rows = load_meaning_modifier_tokens()

    predicate_matches = collect_ordered_matches(lowered, concept_rows, "predicate")
    theme_matches = collect_matches(lowered, concept_rows, "theme")
    scope_matches = collect_matches(
        lowered, [r for r in role_rows if r.get("role") == "scope"], "value"
    )
    target_candidates, target_matches, target_source = target_candidates_from_text(text, role_rows)
    detail_matches = collect_matches(lowered, detail_rows, "detail")
    polarity_matches = collect_matches(
        lowered, [r for r in modifier_rows if r.get("modifier_kind") == "polarity"], "modifier_value"
    )
    modality_matches = collect_matches(
        lowered, [r for r in modifier_rows if r.get("modifier_kind") == "modality"], "modifier_value"
    )
    temporal_matches = collect_matches(
        lowered, [r for r in modifier_rows if r.get("modifier_kind") == "temporal"], "modifier_value"
    )

    predicate, predicate_prov, predicate_ambig = pick_primary(
        predicate_matches, source="rule:meaning_concept_tokens"
    )
    theme, theme_prov, theme_ambig = pick_primary(
        theme_matches, source="rule:meaning_concept_tokens"
    )
    polarity, polarity_prov, polarity_ambig = pick_primary(
        polarity_matches, source="rule:meaning_modifier_tokens"
    )
    modality, modality_prov, modality_ambig = pick_primary(
        modality_matches, source="rule:meaning_modifier_tokens"
    )
    temporal_explicit, temporal_explicit_prov, temporal_ambig = pick_primary(
        temporal_matches, source="rule:meaning_modifier_tokens"
    )
    temporal, temporal_prov = default_temporal(temporal_explicit, temporal_explicit_prov)

    scope_candidates = dedupe_preserve_order([
        "home" if value == "home_if_files" else value
        for value, _span in scope_matches
        if value != "home_if_files"
        or (target_candidates and (predicate == "presence" or theme == "files"))
    ])
    requested_details = dedupe_preserve_order([v for v, _ in detail_matches])
    roles = _roles_from_role_rows(role_rows, lowered)
    composite_followup = composite_followup_from_matches(predicate_matches)

    speech_act, speech_act_prov = _derive_speech_act(text, predicate)
    cardinality, cardinality_prov = _derive_cardinality(lowered, target_candidates)
    mutation_candidate = predicate == "lifecycle_action"

    scope_prov = FieldProvenance(
        source="rule:meaning_role_tokens",
        confidence=0.8 if scope_candidates else 0.0,
        span=scope_matches[0][1] if scope_matches else "",
    )
    target_prov = FieldProvenance(
        source=target_source,
        confidence=0.85 if target_candidates else 0.0,
        span=target_matches[0][1] if target_matches else "",
    )
    detail_prov = FieldProvenance(
        source="rule:meaning_detail_tokens",
        confidence=0.85 if requested_details else 0.0,
        span=detail_matches[0][1] if detail_matches else "",
    )
    roles_prov = FieldProvenance(
        source="rule:meaning_role_tokens", confidence=0.8 if roles else 0.0
    )

    ambiguity = dedupe_preserve_order(
        predicate_ambig + theme_ambig + polarity_ambig + modality_ambig + temporal_ambig
    )

    provenance = {
        "speech_act": speech_act_prov,
        "predicate": predicate_prov,
        "theme": theme_prov,
        "roles": roles_prov,
        "scope_candidates": scope_prov,
        "target_candidates": target_prov,
        "requested_details": detail_prov,
        "temporal": temporal_prov,
        "polarity": polarity_prov,
        "modality": modality_prov,
        "cardinality": cardinality_prov,
    }

    matched_confidences = [
        p.confidence for p in provenance.values() if not p.source.startswith("default_")
    ]
    confidence = min(matched_confidences) if matched_confidences else 0.0

    return MeaningRepresentation(
        speech_act=speech_act,
        predicate=predicate,
        theme=theme,
        roles=roles,
        scope_candidates=scope_candidates,
        target_candidates=target_candidates,
        requested_details=requested_details,
        temporal=temporal,
        polarity=polarity,
        modality=modality,
        cardinality=cardinality,
        mutation_candidate=mutation_candidate,
        ambiguity=ambiguity,
        confidence=confidence,
        provenance=provenance,
        composite_followup=composite_followup,
    )
