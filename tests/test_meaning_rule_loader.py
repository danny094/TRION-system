"""Tests fuer den fail-closed Hot-Reload-Loader — P11 SP1 Aufgabe 3.

Plan-Vorgabe (SP1 Tests): "Loader-Hot-Reload, ungueltiges Schema, leere
Regeln, Provenienz und Konfidenz". Provenienz/Konfidenz sind als
Contract-Eigenschaft bereits in test_meaning_representation_contract.py
abgedeckt (FieldProvenance-Form) — hier liegt der Fokus auf dem Loader
selbst: Hot-Reload, Schemafehler, leere Regeln.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import pytest

from intelligence_modules.cim_skill_rag._meaning_rule_loader import (
    MeaningRuleSchemaError,
    load_rule_rows,
)

_COLUMNS = ("token", "language", "value")


def _write_csv(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def _fresh_cache() -> Dict[str, object]:
    return {"mtime": None, "rows": []}


def test_missing_file_returns_empty_list_no_error(tmp_path: Path):
    csv_path = tmp_path / "missing.csv"
    rows = load_rule_rows(csv_path, _COLUMNS, _fresh_cache())
    assert rows == []


def test_header_only_file_is_valid_empty_rows(tmp_path: Path):
    csv_path = tmp_path / "rules.csv"
    _write_csv(csv_path, "token,language,value\n")
    rows = load_rule_rows(csv_path, _COLUMNS, _fresh_cache())
    assert rows == []


def test_missing_required_column_raises_schema_error(tmp_path: Path):
    csv_path = tmp_path / "rules.csv"
    _write_csv(csv_path, "token,language\nfoo,de\n")
    with pytest.raises(MeaningRuleSchemaError):
        load_rule_rows(csv_path, _COLUMNS, _fresh_cache())


def test_empty_required_cell_raises_schema_error(tmp_path: Path):
    csv_path = tmp_path / "rules.csv"
    _write_csv(csv_path, "token,language,value\nfoo,de,\n")
    with pytest.raises(MeaningRuleSchemaError):
        load_rule_rows(csv_path, _COLUMNS, _fresh_cache())


def test_row_validator_rejection_raises_schema_error(tmp_path: Path):
    csv_path = tmp_path / "rules.csv"
    _write_csv(csv_path, "token,language,value\nfoo,de,bar\n")

    def _reject_everything(row: Dict[str, str], line_no: int) -> None:
        raise MeaningRuleSchemaError(f"abgelehnt in Zeile {line_no}")

    with pytest.raises(MeaningRuleSchemaError):
        load_rule_rows(csv_path, _COLUMNS, _fresh_cache(), row_validator=_reject_everything)


def test_valid_rows_are_parsed_and_stripped(tmp_path: Path):
    csv_path = tmp_path / "rules.csv"
    _write_csv(csv_path, "token,language,value\n foo , de , bar \n")
    rows = load_rule_rows(csv_path, _COLUMNS, _fresh_cache())
    assert rows == [{"token": "foo", "language": "de", "value": "bar"}]


def test_hot_reload_picks_up_changed_content_on_mtime_change(tmp_path: Path):
    csv_path = tmp_path / "rules.csv"
    cache = _fresh_cache()
    _write_csv(csv_path, "token,language,value\nfoo,de,bar\n")
    first = load_rule_rows(csv_path, _COLUMNS, cache)
    assert first == [{"token": "foo", "language": "de", "value": "bar"}]

    _write_csv(csv_path, "token,language,value\nbaz,en,qux\n")
    # mtime künstlich vorstellen, damit der Cache-Vergleich sicher greift
    # (manche Dateisysteme haben eine zu grobe mtime-Auflösung).
    new_time = csv_path.stat().st_mtime + 5
    os.utime(csv_path, (new_time, new_time))

    second = load_rule_rows(csv_path, _COLUMNS, cache)
    assert second == [{"token": "baz", "language": "en", "value": "qux"}]


def test_unchanged_mtime_returns_cached_rows_without_reread(tmp_path: Path):
    csv_path = tmp_path / "rules.csv"
    cache = _fresh_cache()
    _write_csv(csv_path, "token,language,value\nfoo,de,bar\n")
    first = load_rule_rows(csv_path, _COLUMNS, cache)
    cached_source_hash = cache["source_hash"]

    second = load_rule_rows(csv_path, _COLUMNS, cache)
    assert second is first  # gleiches Listenobjekt aus dem Cache
    assert cache["source_hash"] == cached_source_hash


def test_missing_file_sets_cache_fields_to_none(tmp_path: Path):
    csv_path = tmp_path / "missing.csv"
    cache = _fresh_cache()
    load_rule_rows(csv_path, _COLUMNS, cache)
    assert cache["mtime"] is None
    assert cache["source_hash"] is None
    assert cache["rows"] == []


def test_source_hash_changes_when_content_changes(tmp_path: Path):
    csv_path = tmp_path / "rules.csv"
    cache = _fresh_cache()
    _write_csv(csv_path, "token,language,value\nfoo,de,bar\n")
    load_rule_rows(csv_path, _COLUMNS, cache)
    first_hash = cache["source_hash"]

    _write_csv(csv_path, "token,language,value\nfoo,de,changed\n")
    new_time = csv_path.stat().st_mtime + 5
    os.utime(csv_path, (new_time, new_time))
    load_rule_rows(csv_path, _COLUMNS, cache)
    assert cache["source_hash"] != first_hash
