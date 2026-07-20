"""Loader for TMR -> Routing-Signal projection hints — P11 SP1 (Doc 55
Mindestinhalt: "Projektion von Bedeutung auf Routing-Signale").

Diagnose-only: dient ausschliesslich dem sanitisierten Shadow-Trace (Doc 55
A10 / P11-Plan SP1 Stop-Bedingung). Kein Konsument darf diese Hints zur
Laufzeit-Entscheidung verwenden — Routing und Toolwahl bleiben in SP1
unveraendert und lesen `RawSignals.meaning` nicht.

Rule source: intelligence_modules/cim_skill_rag/meaning_signal_projection_rules.csv
Schema: predicate, theme, routing_intent_kind_hint, routing_domain_hint,
routing_evidence_need_hint (alle Pflichtspalten).

Bewusste Vereinfachung: die Hints haengen nur von (predicate, theme) ab,
nicht von gebundenen Targets. Eine target-bewusste Unterscheidung (z.B.
"list" ohne Target vs. "list" mit Target laut Doc 56) ist Aufgabe des
Operation-Contract-Builders in SP2, nicht dieser Diagnose-Projektion.

Hot-reload + fail-closed via _meaning_rule_loader.load_rule_rows().
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from intelligence_modules.cim_skill_rag._meaning_rule_loader import load_rule_rows

_CSV_PATH = Path(__file__).resolve().parent / "meaning_signal_projection_rules.csv"
_REQUIRED_COLUMNS = (
    "predicate",
    "theme",
    "routing_intent_kind_hint",
    "routing_domain_hint",
    "routing_evidence_need_hint",
)
_cache: Dict[str, object] = {"mtime": None, "rows": []}


def load_meaning_signal_projection_rules() -> List[Dict[str, str]]:
    """Return projection-rule rows keyed conceptually by (predicate, theme)."""
    return load_rule_rows(_CSV_PATH, _REQUIRED_COLUMNS, _cache)
