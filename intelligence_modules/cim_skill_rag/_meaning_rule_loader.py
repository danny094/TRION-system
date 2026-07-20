"""Shared fail-closed hot-reload helper for TMR-Regel-CSVs (P11 SP1).

Kein bestehender Loader in diesem Verzeichnis erzwingt fail-closed bei
Schemafehlern (sie ueberspringen ungueltige Zeilen stillschweigend, z.B.
live_claim_loader.py: `if token and kind: ...`). TMR braucht laut P11-Plan
SP1 Aufgabe 3 explizit "Schemafehlern fail-closed", deshalb ein eigener,
wiederverwendbarer Helfer statt einer 1:1-Kopie des bestehenden Musters.

Verhalten (bewusst getrennt, siehe SP1-Tests "leere Regeln" vs. "ungueltiges
Schema"):
- Datei fehlt: leere Zeilenliste, kein Fehler. TMR ist reiner Shadow-Trace
  (Doc55 A10) — eine fehlende Regel-Datei darf den produktiven Pfad nicht
  zum Absturz bringen, sie liefert dann nur keine Signale (leer statt
  erfunden, siehe MeaningRepresentation-Invariante).
- Datei vorhanden, nur Header oder keine Datenzeilen: leere Zeilenliste,
  gueltig.
- Header fehlt eine Pflichtspalte ODER eine Pflichtzelle ist leer ODER der
  optionale `row_validator` lehnt eine Zeile ab: `MeaningRuleSchemaError`,
  keine stille Teilverarbeitung.

Quellhash (sha256 der Rohbytes) und mtime liegen nach dem Laden im
uebergebenen `cache`-Dict unter den Keys "source_hash"/"mtime".
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


class MeaningRuleSchemaError(ValueError):
    """Eine TMR-Regel-CSV hat einen Schemafehler (fail-closed, kein Skip)."""


def load_rule_rows(
    csv_path: Path,
    required_columns: Tuple[str, ...],
    cache: Dict[str, object],
    *,
    row_validator: Optional[Callable[[Dict[str, str], int], None]] = None,
) -> List[Dict[str, str]]:
    """Hot-reload eine Regel-CSV, fail-closed bei Schemafehlern.

    Args:
        csv_path: Pfad der Regel-CSV.
        required_columns: Spalten, die in jeder Zeile nicht-leer sein muessen.
        cache: Modul-eigenes Cache-Dict des Aufrufers (mtime/rows/source_hash).
        row_validator: Optionale zusaetzliche Pruefung pro Zeile (z.B. "mind.
            eine von zwei Spalten muss gefuellt sein"). Muss bei Verstoss
            MeaningRuleSchemaError werfen.
    """
    if not csv_path.exists():
        cache["mtime"] = None
        cache["path"] = str(csv_path)
        cache["source_hash"] = None
        cache["rows"] = []
        return []

    mtime = csv_path.stat().st_mtime
    if cache.get("mtime") == mtime and cache.get("path") == str(csv_path):
        return cache["rows"]  # type: ignore[return-value]

    source_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    rows: List[Dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = tuple(reader.fieldnames or ())
        missing = [c for c in required_columns if c not in header]
        if missing:
            raise MeaningRuleSchemaError(
                f"{csv_path.name}: fehlende Pflichtspalte(n) {missing}"
            )
        for line_no, row in enumerate(reader, start=2):
            clean = {k: str(v or "").strip() for k, v in row.items()}
            for col in required_columns:
                if not clean.get(col):
                    raise MeaningRuleSchemaError(
                        f"{csv_path.name}:{line_no}: Pflichtspalte '{col}' ist leer"
                    )
            if row_validator is not None:
                row_validator(clean, line_no)
            rows.append(clean)

    cache["mtime"] = mtime
    cache["path"] = str(csv_path)
    cache["source_hash"] = source_hash
    cache["rows"] = rows
    return rows
