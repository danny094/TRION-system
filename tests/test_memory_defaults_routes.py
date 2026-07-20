"""Tests fuer /api/settings/memory/defaults plus den settings-getriebenen
Default-Builder in core/conversation_meta/defaults.py.

Codex-konforme Aufteilung:
- persistiert: memory_mode, do_not_remember, max_memory_hits
- abgeleitet (nicht persistiert): allow_long_term_write, allow_global_memory_read

Plus: bestaetigt, dass build_default_conversation_meta die settings-Werte liest.

Helfer + die autouse `_isolate_settings`-Fixture liegen in
tests/_memory_defaults_routes_helpers.py (Doc 07s 200-Zeilen-Grenze, siehe
dortiges Modul-Docstring). Der Import von `_isolate_settings` ist bewusst
ungenutzt im Code dieser Datei - pytest erkennt die Fixture allein dadurch,
dass der Name im Modul-Namensraum vorhanden ist.
"""

import asyncio

import pytest

from tests._memory_defaults_routes_helpers import (  # noqa: F401
    ROOT,
    _isolate_settings,
    _load_memory_defaults_routes,
)


def test_get_returns_hardcoded_default_when_no_setting():
    routes = _load_memory_defaults_routes()
    response = asyncio.run(routes.get_memory_defaults())
    assert response["defaults"]["memory_mode"] == "global_enabled"
    assert response["defaults"]["do_not_remember"] is False
    assert response["defaults"]["max_memory_hits"] == 5


def test_get_derives_allow_long_term_write_for_default():
    routes = _load_memory_defaults_routes()
    response = asyncio.run(routes.get_memory_defaults())
    assert response["derived"]["allow_long_term_write"] is True
    assert response["derived"]["allow_global_memory_read"] is True


def test_post_radio_ja_dauerhaft_maps_to_global_enabled():
    routes = _load_memory_defaults_routes()
    update = routes.MemoryDefaultsUpdate(memory_mode="global_enabled", do_not_remember=False)
    response = asyncio.run(routes.update_memory_defaults(update))
    assert response["defaults"]["memory_mode"] == "global_enabled"
    assert response["derived"]["allow_long_term_write"] is True
    assert response["derived"]["allow_global_memory_read"] is True


def test_post_radio_nur_diese_unterhaltung_maps_correctly():
    routes = _load_memory_defaults_routes()
    update = routes.MemoryDefaultsUpdate(memory_mode="conversation_only", do_not_remember=False)
    response = asyncio.run(routes.update_memory_defaults(update))
    assert response["defaults"]["memory_mode"] == "conversation_only"
    assert response["derived"]["allow_global_memory_read"] is False
    assert response["derived"]["allow_long_term_write"] is True


def test_post_radio_nichts_disables_writes_and_reads():
    routes = _load_memory_defaults_routes()
    update = routes.MemoryDefaultsUpdate(memory_mode="disabled", do_not_remember=True)
    response = asyncio.run(routes.update_memory_defaults(update))
    assert response["defaults"]["memory_mode"] == "disabled"
    assert response["defaults"]["do_not_remember"] is True
    assert response["derived"]["allow_global_memory_read"] is False
    assert response["derived"]["allow_long_term_write"] is False


def test_post_max_memory_hits_validates_bounds():
    routes = _load_memory_defaults_routes()
    update = routes.MemoryDefaultsUpdate(max_memory_hits=12)
    response = asyncio.run(routes.update_memory_defaults(update))
    assert response["defaults"]["max_memory_hits"] == 12


def test_post_rejects_invalid_max_memory_hits():
    routes = _load_memory_defaults_routes()
    with pytest.raises(Exception):
        routes.MemoryDefaultsUpdate(max_memory_hits=999)


def test_post_rejects_unknown_field():
    routes = _load_memory_defaults_routes()
    with pytest.raises(Exception):
        routes.MemoryDefaultsUpdate(allow_long_term_write=True)  # type: ignore[call-arg]


def test_post_rejects_empty_payload():
    routes = _load_memory_defaults_routes()
    update = routes.MemoryDefaultsUpdate()
    with pytest.raises(Exception):
        asyncio.run(routes.update_memory_defaults(update))


def test_default_builder_picks_up_disabled_mode():
    """Settings -> build_default_conversation_meta-Schleife."""
    routes = _load_memory_defaults_routes()
    update = routes.MemoryDefaultsUpdate(memory_mode="disabled", do_not_remember=True)
    asyncio.run(routes.update_memory_defaults(update))

    from core.conversation_meta.defaults import build_default_conversation_meta

    meta = build_default_conversation_meta("new-conv")
    assert meta.memory.mode.value == "disabled"
    assert meta.memory.do_not_remember is True
    assert meta.memory.scopes == []


def test_default_builder_picks_up_conversation_only_mode():
    routes = _load_memory_defaults_routes()
    update = routes.MemoryDefaultsUpdate(memory_mode="conversation_only", do_not_remember=False)
    asyncio.run(routes.update_memory_defaults(update))

    from core.conversation_meta.defaults import build_default_conversation_meta

    meta = build_default_conversation_meta("new-conv")
    assert meta.memory.mode.value == "conversation_only"
    assert meta.memory.do_not_remember is False
    assert len(meta.memory.scopes) == 1
    assert meta.memory.scopes[0].namespace == "session"
    assert meta.memory.scopes[0].siloed is True


def test_max_memory_hits_propagates_to_self_context():
    routes = _load_memory_defaults_routes()
    asyncio.run(routes.update_memory_defaults(routes.MemoryDefaultsUpdate(max_memory_hits=12)))

    from core.conversation_meta.defaults import get_default_max_memory_hits

    assert get_default_max_memory_hits() == 12


def test_no_persistence_of_derived_fields():
    """Anti-Drift: derived Felder duerfen nicht im Settings-Store landen.

    Codex-Linie: allow_long_term_write und allow_global_memory_read sind
    Projektion, nicht Eingabe. Wenn jemand sie irrtuemlich persistiert,
    haben wir zwei Wahrheiten fuer eine Frage (Doc 13-Verstoss).
    """
    routes = _load_memory_defaults_routes()
    asyncio.run(routes.update_memory_defaults(routes.MemoryDefaultsUpdate(memory_mode="disabled", do_not_remember=True)))

    stored_keys = set(routes.settings.settings.keys())
    forbidden_in_store = {"MEMORY_ALLOW_LONG_TERM_WRITE", "MEMORY_ALLOW_GLOBAL_MEMORY_READ"}
    overlap = stored_keys & forbidden_in_store
    assert overlap == set(), (
        f"Drift: abgeleitete Felder im Settings-Store: {overlap}. "
        "Sie muessen aus memory_mode + do_not_remember im Backend abgeleitet werden."
    )


def test_get_reads_env_defaults_when_no_override(monkeypatch):
    routes = _load_memory_defaults_routes()
    monkeypatch.setenv(routes.MEMORY_DEFAULT_MODE_KEY, "conversation_only")
    monkeypatch.setenv(routes.MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY, "false")
    monkeypatch.setenv(routes.MEMORY_DEFAULT_MAX_MEMORY_HITS_KEY, "9")

    response = asyncio.run(routes.get_memory_defaults())

    assert response["defaults"]["memory_mode"] == "conversation_only"
    assert response["defaults"]["do_not_remember"] is False
    assert response["defaults"]["max_memory_hits"] == 9
    assert response["sources"]["memory_mode"] == "env"


def test_update_never_writes_to_real_repo_settings_file(tmp_path):
    """Codex Checkpoint 4 P1 (2. Runde), Regressionsbeweis: ein .set()-Aufruf
    in update_memory_defaults() darf wegen der _isolate_settings-Fixture
    ausschliesslich die isolierte tmp_path-Datei beschreiben, niemals die
    echte, im Repo getrackte config/settings.json - genau das war zuvor
    waehrend eines breiten Testlaufs passiert (siehe Fixture-Docstring in
    tests/_memory_defaults_routes_helpers.py).
    """
    real_settings_path = ROOT / "config" / "settings.json"
    before = real_settings_path.read_text(encoding="utf-8") if real_settings_path.exists() else None

    routes = _load_memory_defaults_routes()
    isolated_path = routes.settings._settings_path
    assert isolated_path != real_settings_path
    assert isolated_path.parent == tmp_path

    asyncio.run(routes.update_memory_defaults(routes.MemoryDefaultsUpdate(max_memory_hits=7)))

    assert isolated_path.exists(), "Settings-Schreibzugriff muss auf der isolierten Datei landen"
    after = real_settings_path.read_text(encoding="utf-8") if real_settings_path.exists() else None
    assert after == before, "Die echte config/settings.json darf von Tests niemals veraendert werden"
