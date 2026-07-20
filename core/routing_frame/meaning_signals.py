"""Low-level Matching-Helfer fuer den TMR-Builder — P11 SP1.

Reine Funktionen ohne Seiteneffekt: Wortgrenzen-Matching gegen die
hot-reloadbaren Regeltabellen aus intelligence_modules/cim_skill_rag/ und
deterministisches Aufloesen mehrdeutiger Treffer auf einen Primaerwert plus
Ambiguitaets-Restliste. Kein LLM-Call (Doc 55 A2), keine Operation/Toolwahl
(Doc 55 A1).

core liest die hot-reload-faehigen Regeln nur; es schreibt sie nicht
(Doc 55 Implementierungsgrenzen).
"""

from __future__ import annotations

import re
from typing import Dict, List, Sequence, Tuple

from core.routing_frame.contracts import FieldProvenance

_EXPLICIT_CONFIDENCE = 0.85
_AMBIGUOUS_CONFIDENCE = 0.5
_DEFAULT_CONFIDENCE = 0.5


def contains_token(lowered_text: str, token: str) -> bool:
    """Wortgrenzen-Suche (kein freies Substring-Matching, z.B. "kann" darf
    nicht in "bekannt" treffen). Mehrwort-Tokens ("home space") funktionieren
    unveraendert, da \\b auch an Leerzeichen-Grenzen greift.
    """

    pattern = r"\b" + re.escape(token.lower()) + r"\b"
    return re.search(pattern, lowered_text) is not None


def collect_matches(
    lowered_text: str, rows: Sequence[Dict[str, str]], value_column: str
) -> List[Tuple[str, str]]:
    """Liefert (value, token)-Paare aller Regelzeilen, deren Token im Text
    vorkommt und deren `value_column` nicht leer ist. Reihenfolge = Zeilen-
    reihenfolge der Quelltabelle (deterministisch, keine Sortierung nach
    Relevanz-Score).
    """

    matches: List[Tuple[str, str]] = []
    for row in rows:
        value = row.get(value_column, "")
        if not value:
            continue
        token = row.get("token", "")
        if token and contains_token(lowered_text, token):
            matches.append((value, token))
    return matches


def collect_ordered_matches(
    lowered_text: str, rows: Sequence[Dict[str, str]], value_column: str
) -> List[Tuple[str, str]]:
    """Like collect_matches(), but ordered by the matched token position.

    Composite meaning rules need an ordered predicate sequence. The source is
    still the same structured token table; raw text positions are used only to
    preserve match order and are not stored in contracts or events.
    """

    positioned: List[Tuple[int, int, str, str]] = []
    for row_index, row in enumerate(rows):
        value = row.get(value_column, "")
        token = row.get("token", "")
        if not value or not token:
            continue
        pattern = r"\b" + re.escape(token.lower()) + r"\b"
        match = re.search(pattern, lowered_text)
        if match is not None:
            positioned.append((match.start(), row_index, value, token))
    positioned.sort(key=lambda item: (item[0], item[1]))
    return [(value, token) for _pos, _row, value, token in positioned]


def pick_primary(
    matches: Sequence[Tuple[str, str]], *, source: str
) -> Tuple[str, FieldProvenance, Tuple[str, ...]]:
    """Loest eine Match-Liste auf einen Primaerwert plus Provenance plus
    Ambiguitaets-Restliste auf. Leer statt erfunden: keine Treffer -> "".
    Mehrere unterschiedliche Werte -> erster Wert ist primaer (Zeilen-
    Reihenfolge), alle uebrigen distinkten Werte wandern in `ambiguity`.
    """

    if not matches:
        return "", FieldProvenance(source="default_empty", confidence=0.0), ()

    distinct: List[str] = []
    first_span: Dict[str, str] = {}
    for value, token in matches:
        if value not in distinct:
            distinct.append(value)
            first_span[value] = token

    primary = distinct[0]
    if len(distinct) == 1:
        provenance = FieldProvenance(
            source=source, confidence=_EXPLICIT_CONFIDENCE, span=first_span[primary]
        )
        return primary, provenance, ()

    provenance = FieldProvenance(
        source=source, confidence=_AMBIGUOUS_CONFIDENCE, span=first_span[primary]
    )
    return primary, provenance, tuple(distinct[1:])


def dedupe_preserve_order(values: Sequence[str]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def default_temporal(
    explicit_value: str, explicit_provenance: FieldProvenance
) -> Tuple[str, FieldProvenance]:
    """Doc 55 Beispieltabelle fordert temporal=current auch ohne explizites
    Zeit-Token (z.B. "Was laeuft zuhause?" hat kein "jetzt"/"now"). Default
    greift nur, wenn kein expliziter Modifier-Treffer vorliegt; ein
    expliziter Treffer (auch "past") hat immer Vorrang.
    """

    if explicit_value:
        return explicit_value, explicit_provenance
    return "current", FieldProvenance(source="default_current", confidence=_DEFAULT_CONFIDENCE)
