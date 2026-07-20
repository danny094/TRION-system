"""Regressionsbeweis fuer Codex Checkpoint 4 P1 (3. Runde).

Die `_isolate_settings`-Fixture in tests/_memory_defaults_routes_helpers.py
muss nach jedem Test, der die drei MEMORY_DEFAULT_*-Keys im globalen
SettingsManager-Singleton entfernt, deren urspruenglichen Wert (aus der
echten config/settings.json geladen, z.B. MEMORY_DEFAULT_MODE="disabled",
Commit 9c7ed93) im Singleton wiederherstellen - nicht nur die Datei auf der
Platte unveraendert lassen. Letzteres deckt bereits
test_update_never_writes_to_real_repo_settings_file in
test_memory_defaults_routes.py ab; dieser Test deckt die davon unabhaengige
In-Memory-Drift ab, die Codex in der 3. Runde separat bemaengelt hat.

Bewusst eine eigene Datei (Doc 07s 200-Zeilen-Grenze, Single-Responsibility):
dieser Test importiert die `_isolate_settings`-Fixture NICHT - er beobachtet
den Singleton von AUSSEN, vor und nach einem In-Process-Lauf der isolierten
Testsuite, im selben Python-Prozess. Ein neuer Prozess wuerde den Singleton
immer frisch von der Festplatte laden und koennte In-Memory-Drift gar nicht
sichtbar machen.
"""

import pytest

from tests._memory_defaults_routes_helpers import ROOT, _load_memory_defaults_routes


def test_isolate_settings_fixture_restores_singleton_after_suite_runs():
    routes = _load_memory_defaults_routes()
    mode_key = routes.MEMORY_DEFAULT_MODE_KEY
    do_not_remember_key = routes.MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY
    max_hits_key = routes.MEMORY_DEFAULT_MAX_MEMORY_HITS_KEY

    def snapshot():
        return {
            mode_key: routes.settings.settings.get(mode_key, "<absent>"),
            do_not_remember_key: routes.settings.settings.get(do_not_remember_key, "<absent>"),
            max_hits_key: routes.settings.settings.get(max_hits_key, "<absent>"),
        }

    before = snapshot()

    target = ROOT / "tests" / "test_memory_defaults_routes.py"
    exit_code = pytest.main(["-q", str(target)])

    after = snapshot()

    assert exit_code != pytest.ExitCode.NO_TESTS_COLLECTED, (
        "Die Suite muss tatsaechlich gelaufen sein, sonst ist dieser Beweis wertlos."
    )
    assert after == before, (
        "Die _isolate_settings-Fixture muss den urspruenglichen Singleton-Zustand "
        f"nach jedem Test wiederherstellen. Vorher: {before}, nachher: {after}."
    )
