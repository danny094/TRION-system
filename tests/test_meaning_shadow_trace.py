"""Tests fuer den sanitisierten TMR-Shadow-Trace — P11 SP1 (Doc55 A10/A11).

Deckt ab:
- sanitisierte Struktur ist JSON-faehig und enthaelt keine rohen Volltexte,
- meaning=None -> fester Platzhalter statt Fehler,
- RoutingFrame bleibt unveraendert (kein "meaning"-Feld, A10).
"""

from __future__ import annotations

import dataclasses
import json

from core.routing_frame.contracts import RoutingFrame
from core.routing_frame.meaning import build_meaning_representation
from core.routing_frame.meaning_shadow_trace import sanitize_meaning_for_shadow_trace


def test_sanitize_meaning_for_shadow_trace_is_json_serializable():
    meaning = build_meaning_representation("Zeig Ports und Mounts von trion-home")
    trace = sanitize_meaning_for_shadow_trace(meaning)
    json.dumps(trace)  # darf nicht werfen


def test_sanitize_meaning_for_shadow_trace_status_ok_fields():
    meaning = build_meaning_representation("Starte trion-home")
    trace = sanitize_meaning_for_shadow_trace(meaning)
    assert trace["status"] == "ok"
    assert trace["predicate"] == "lifecycle_action"
    assert trace["target_candidates"] == ["trion-home"]
    assert trace["mutation_candidate"] is True
    assert "provenance" in trace and isinstance(trace["provenance"], dict)


def test_sanitize_meaning_for_shadow_trace_none_returns_placeholder():
    assert sanitize_meaning_for_shadow_trace(None) == {"status": "unavailable"}


def test_sanitize_meaning_for_shadow_trace_does_not_contain_raw_full_text():
    raw_text = "Was laeuft im geheimen Projekt Aurora zuhause?"
    meaning = build_meaning_representation(raw_text)
    trace = sanitize_meaning_for_shadow_trace(meaning)
    serialized = json.dumps(trace)
    assert "Aurora" not in serialized
    assert "geheimen Projekt" not in serialized


def test_routing_frame_has_no_meaning_field_doc55_a10():
    field_names = {f.name for f in dataclasses.fields(RoutingFrame)}
    assert "meaning" not in field_names
