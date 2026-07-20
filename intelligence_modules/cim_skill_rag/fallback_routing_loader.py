"""Lädt Fallback-Routing-Regeln aus fallback_routing_rules.csv.

Jede Regel definiert eine Bedingung (condition_type + condition_value,
optional requires_also als AND-Verknüpfung) und eine Strategie
(aktuell nur ``first_available``).

Mtime-basiertes Hot-Reload — kein @lru_cache.

PIANO 1.0 B3-Vollfix: should_fallback_to_first_available_tool in
core/thinking/fallback/tools.py enthält keine hardcodierten
Frame-Werte mehr. (2026-06-12)
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List, NamedTuple, Optional

_CSV_PATH = Path(__file__).parent / "fallback_routing_rules.csv"

_cache: dict[str, object] = {"mtime": None, "data": []}


class FallbackRoutingRule(NamedTuple):
    condition_type: str   # intent_kind | execution_mode | classifier_category
    condition_value: str  # Frame-Wert, der gematcht werden muss
    requires_also: Optional[str]  # "field:value" (AND-Bedingung) oder None
    strategy: str         # first_available


def load_fallback_routing_rules() -> List[FallbackRoutingRule]:
    """Gibt alle Fallback-Routing-Regeln aus der CSV zurück.

    Returns:
        Liste von FallbackRoutingRule-Einträgen, leer wenn CSV fehlt.
    """
    if not _CSV_PATH.exists():
        return []
    mtime = _CSV_PATH.stat().st_mtime
    if _cache["mtime"] == mtime:
        return _cache["data"]  # type: ignore[return-value]

    rules: list[FallbackRoutingRule] = []
    with _CSV_PATH.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            condition_type = str(row.get("condition_type") or "").strip()
            condition_value = str(row.get("condition_value") or "").strip()
            requires_also = str(row.get("requires_also") or "").strip() or None
            strategy = str(row.get("strategy") or "").strip()
            if condition_type and condition_value and strategy:
                rules.append(
                    FallbackRoutingRule(condition_type, condition_value, requires_also, strategy)
                )

    _cache["mtime"] = mtime
    _cache["data"] = rules
    return rules
