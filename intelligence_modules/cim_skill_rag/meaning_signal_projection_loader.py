"""Single TMR -> Routing-Signal projection owner — P11 SP8 R5.

The CSV is the productive projection source. Exact predicate/theme rules win
over the explicit ``*/theme`` fallback; ``inherit`` leaves an existing typed
routing signal unchanged.

Rule source: intelligence_modules/cim_skill_rag/meaning_signal_projection_rules.csv
Schema: predicate, theme, routing_intent_kind_hint, routing_domain_hint,
routing_evidence_need_hint (alle Pflichtspalten).

Bewusste Vereinfachung: die Hints haengen nur von (predicate, theme) ab,
nicht von gebundenen Targets. Eine target-bewusste Unterscheidung (z.B.
"list" ohne Target vs. "list" mit Target laut Doc 56) ist Aufgabe des
Operation-Contract-Builders, nicht dieses Projektionsowners.

Hot-reload + fail-closed via _meaning_rule_loader.load_rule_rows().
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from intelligence_modules.cim_skill_rag._meaning_rule_loader import (
    MeaningRuleSchemaError,
    load_rule_rows,
)

_CSV_PATH = Path(__file__).resolve().parent / "meaning_signal_projection_rules.csv"
_REQUIRED_COLUMNS = (
    "predicate",
    "theme",
    "routing_intent_kind_hint",
    "routing_domain_hint",
    "routing_evidence_need_hint",
)
_cache: Dict[str, object] = {"mtime": None, "rows": []}
_INHERIT = "inherit"
_MIN_PROJECTION_CONFIDENCE = 0.85


def load_meaning_signal_projection_rules() -> List[Dict[str, str]]:
    """Return projection-rule rows keyed conceptually by (predicate, theme)."""
    rows = load_rule_rows(_CSV_PATH, _REQUIRED_COLUMNS, _cache)
    seen = set()
    for row in rows:
        key = (row["predicate"], row["theme"])
        if key in seen:
            raise MeaningRuleSchemaError(
                f"{_CSV_PATH.name}: duplicate predicate/theme projection {key!r}"
            )
        seen.add(key)
    return rows


def project_meaning_signals(meaning: object) -> Dict[str, str]:
    """Project one typed meaning into optional routing signal overrides."""
    predicate = str(getattr(meaning, "predicate", "") or "").strip()
    theme = str(getattr(meaning, "theme", "") or "").strip()
    if not theme or tuple(getattr(meaning, "ambiguity", ()) or ()):
        return {}
    provenance = getattr(meaning, "provenance", {})
    if not isinstance(provenance, dict) or not _trusted(provenance.get("theme")):
        return {}
    if predicate and not _trusted(provenance.get("predicate")):
        return {}

    rows = load_meaning_signal_projection_rules()
    exact = next(
        (row for row in rows if row["predicate"] == predicate and row["theme"] == theme),
        None,
    )
    selected = exact or next(
        (row for row in rows if row["predicate"] == "*" and row["theme"] == theme),
        None,
    )
    if selected is None:
        return {}
    return {
        "intent_kind": _projected_value(selected["routing_intent_kind_hint"]),
        "domain": _projected_value(selected["routing_domain_hint"]),
        "evidence_need": _projected_value(selected["routing_evidence_need_hint"]),
    }


def _projected_value(value: str) -> str:
    return "" if value == _INHERIT else value


def _trusted(provenance: object) -> bool:
    confidence = getattr(provenance, "confidence", 0.0)
    return isinstance(confidence, (int, float)) and confidence >= _MIN_PROJECTION_CONFIDENCE
