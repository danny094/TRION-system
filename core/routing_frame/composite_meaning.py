"""Canonical composite follow-up projection for TMR.

This module matches already structured, ordered predicate matches against the
dedicated composite meaning rule source. It is observe/source projection for
MeaningRepresentation only; it does not derive operations from raw text,
targets, evidence, tool names, or runtime behavior.
"""

from __future__ import annotations

from typing import Sequence, Tuple

from core.routing_frame.contracts import CompositeFollowupIntent
from core.routing_frame.meaning_signals import dedupe_preserve_order
from intelligence_modules.cim_skill_rag.meaning_composite_loader import (
    load_meaning_composite_rules,
)


def composite_followup_from_matches(
    predicate_matches: Sequence[Tuple[str, str]],
) -> CompositeFollowupIntent | None:
    semantic_sequence = dedupe_preserve_order([value for value, _token in predicate_matches])
    if len(semantic_sequence) < 2:
        return None
    try:
        rules = load_meaning_composite_rules()
    except Exception:
        return None
    for rule in rules:
        if rule.semantic_sequence == semantic_sequence:
            return CompositeFollowupIntent(
                semantic_sequence=rule.semantic_sequence,
                intent_sequence=rule.intent_sequence,
            )
    return None
