"""Gemeinsame Test-Helfer + Fixture fuer tests/test_memory_defaults_routes.py.

Kein `test_`-Praefix - wird von pytest nicht als Testmodul eingesammelt
(gleiches Vorgehen wie tests/_tool_manifest_mirror_reconcile_helpers.py).
Ausgelagert aus test_memory_defaults_routes.py, weil Codex Checkpoint 4 P1
(2. Runde) die `_isolate_settings`-Fixture um die settings.json-Isolation
erweitert hat und die Testdatei dadurch ueber Doc 07s 200-Zeilen-Grenze
geschoben haette - keine Ausnahme fuer Testdateien.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _resolve_admin_api_dir() -> Path:
    candidates = [ROOT / "adapters" / "admin-api", Path("/app"), ROOT]
    for path in candidates:
        if (path / "memory_defaults_routes.py").exists():
            return path
    raise FileNotFoundError("memory_defaults_routes.py not found in any known layout")


ADMIN_API_DIR = _resolve_admin_api_dir()


def _load_memory_defaults_routes():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    spec = importlib.util.spec_from_file_location(
        "trion_memory_defaults_routes_for_test",
        ADMIN_API_DIR / "memory_defaults_routes.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_ABSENT = object()


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch, tmp_path):
    """Setze die Memory-Default-Keys fuer jeden Test frisch zurueck UND
    isoliere die Persistenz vollstaendig von der echten config/settings.json.

    Codex Checkpoint 4 P1 (2. Runde): routes.settings ist
    utils.settings.manager.settings - ein echtes Singleton, beim Modul-Import
    bereits auf config/settings.json geladen (Repo-lokaler Fallback, siehe
    SettingsManager._load()). Ein blosses Leeren der drei Memory-Default-Keys
    im In-Memory-Dict verhindert NICHT, dass .set() in
    update_memory_defaults() ueber _save() synchron auf die echte Repo-Datei
    schreibt - genau das hat zuvor einen breiten Testlauf die echte
    config/settings.json ueberschreiben lassen.

    SettingsManager._save() versucht IMMER zuerst self._settings_path und
    kehrt bei Erfolg sofort zurueck (Fallback auf weitere Kandidaten nur bei
    Schreibfehler) - das Patchen von _settings_path auf einen Pfad unter
    tmp_path reicht daher aus, um jeden Schreibzugriff fuer die Dauer dieses
    Tests vollstaendig auf ein isoliertes Verzeichnis umzuleiten,
    unabhaengig davon, was im In-Memory-Dict steht. TRION_SETTINGS_FILE wird
    zusaetzlich gebunden (Codex-Vorgabe explizit so verlangt), auch wenn der
    bereits laufende Singleton es fuer sich genommen nicht erneut auswertet.

    Codex Checkpoint 4 P1 (3. Runde): ein direktes `del settings.settings[key]`
    vor UND nach dem Test loescht den Key dauerhaft, statt den urspruenglich
    aus config/settings.json geladenen Wert (z.B. MEMORY_DEFAULT_MODE=
    "disabled") im Singleton wiederherzustellen.

    WICHTIG, beim Implementieren dieser 3. Runde selbst gefunden (nicht von
    Codex vorgegeben): `monkeypatch.delitem(dic, key, raising=False)` zeichnet
    NUR dann einen Undo-Eintrag auf, wenn der Key zum Zeitpunkt des Aufrufs
    bereits EXISTIERT (siehe _pytest.monkeypatch.MonkeyPatch.delitem - der
    `else`-Zweig mit `self._setitem.append(...)` wird nur betreten, wenn
    `name in dic`). War ein Key (z.B. MEMORY_DEFAULT_MAX_MEMORY_HITS) zu
    Testbeginn ABWESEND, registriert delitem(..., raising=False) ueberhaupt
    nichts - setzt ein Test diesen Key waehrend des Laufs (z.B. via
    update_memory_defaults()), bleibt er nach dem Test dauerhaft im Singleton
    haengen, obwohl er vorher nicht da war. Bewiesen durch einen In-Process-
    Lauf von test_memory_defaults_routes.py vor/nach Snapshot-Vergleich
    (tests/test_memory_defaults_settings_singleton_restoration.py).

    Deshalb wird hier NICHT auf monkeypatch fuer die drei Keys vertraut,
    sondern der vollstaendige Originalzustand (Wert oder `_ABSENT`-Sentinel)
    manuell gesichert und nach dem Test exakt wiederhergestellt - das ist
    Codex' explizit genannte Alternative ("vorherige Werte vollstaendig
    sichern und wiederherstellen").
    """
    routes = _load_memory_defaults_routes()
    tmp_settings_path = tmp_path / "settings.json"
    monkeypatch.setenv("TRION_SETTINGS_FILE", str(tmp_settings_path))
    monkeypatch.setattr(routes.settings, "_settings_path", tmp_settings_path)

    keys = (
        routes.MEMORY_DEFAULT_MODE_KEY,
        routes.MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY,
        routes.MEMORY_DEFAULT_MAX_MEMORY_HITS_KEY,
    )
    original_values = {key: routes.settings.settings.get(key, _ABSENT) for key in keys}
    for key in keys:
        routes.settings.settings.pop(key, None)

    yield

    for key, value in original_values.items():
        if value is _ABSENT:
            routes.settings.settings.pop(key, None)
        else:
            routes.settings.settings[key] = value
