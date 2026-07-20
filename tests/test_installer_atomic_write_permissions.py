"""P11.0 SP2 - Rechte-Erhalt im atomaren Writer (Codex Checkpoint 3, Runde 4+5 P1).

Runde 4: ohne expliziten chmod vor os.replace() haette eine bestehende
Zieldatei (z. B. mcp.json oder mcp_registry.json mit vom Docker-Entrypoint
gesetzten Gruppenrechten) ihre Rechte verloren. atomic_write_text()
uebertraegt jetzt den Modus der bestehenden Zieldatei auf die Tempdatei.

Runde 5: fuer eine NEUE Zieldatei darf kein Standardmodus ueber ein
Python-seitiges os.umask()-Lesen ermittelt werden - die Umask ist
prozessweit, nicht threadlokal; ein kurzzeitiges Setzen/Zuruecksetzen
oeffnete ein Race fuer parallele Threads. Die Tempdatei wird daher per
O_CREAT|O_EXCL angelegt; der Kernel maskiert den Modus atomar.

Runde 6: existiert die Zieldatei bereits, war die Tempdatei bisher trotzdem
immer mit 0o666 (umask-maskiert) angelegt worden - der engere Zielmodus kam
erst NACH dem Schreiben per chmod(). Waehrend des Schreibfensters war die
Tempdatei dadurch breiter lesbar als die Zieldatei erlaubt (reproduziert:
Ziel 0600, Tempdatei waehrend des Schreibens 0644). _create_unique_tmp_file()
erhaelt den bestehenden Zielmodus jetzt direkt als Erzeugungsmodus - die
Umask kann ihn nur enger, nie weiter machen.

Eigene Datei statt Erweiterung von test_tool_manifest_mirror_lifecycle.py
bzw. test_mcp_installer_route_wiring.py, um beide unter der 200-Zeilen-Grenze
aus Doc 07 zu halten (Doc 07: "wird eine Datei groesser, wird sie
aufgeteilt").
"""
import json
import os
import stat

from mcp.installer_common import atomic_write_text
from mcp.installer_registry import upsert_registry_entry


def _bind_registry(monkeypatch, tmp_path):
    registry_path = tmp_path / "mcp_registry.json"
    import mcp.config as mcp_config

    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", registry_path)
    return registry_path


def test_upsert_registry_entry_preserves_existing_registry_file_permissions(monkeypatch, tmp_path):
    registry_path = _bind_registry(monkeypatch, tmp_path)
    registry_path.write_text(json.dumps({"existing": {"enabled": True}}), encoding="utf-8")
    os.chmod(registry_path, 0o664)

    upsert_registry_entry(
        "demo",
        {
            "enabled": True,
            "transport": "http",
            "url": "http://demo:8000/mcp",
            "description": "Demo MCP",
            "version": "1.0.0",
        },
    )

    assert stat.S_IMODE(registry_path.stat().st_mode) == 0o664


def test_atomic_write_text_never_reads_or_sets_process_umask(monkeypatch, tmp_path):
    # Codex-Befund (Checkpoint 3, Runde 5 P1): os.umask() ist prozessweit,
    # nicht threadlokal - ein kurzzeitiges Setzen/Zuruecksetzen zur Ermittlung
    # des aktuellen Werts oeffnete ein Zeitfenster, in dem parallele Threads
    # mit der falschen effektiven Umask Dateien anlegen konnten (reproduziert:
    # Umask 0o077, paralleler Thread legt 0o666 statt 0o600 an). Dieser Test
    # beweist strukturell, dass atomic_write_text() os.umask() ueberhaupt
    # nicht mehr aufruft - der Race ist damit per Konstruktion ausgeschlossen.
    calls = []
    monkeypatch.setattr(os, "umask", lambda *a, **k: calls.append(a) or 0)

    atomic_write_text(tmp_path / "new.json", "{}")
    atomic_write_text(tmp_path / "new.json", "{}")  # existierende Zieldatei

    assert calls == []


def test_tmp_file_is_never_wider_than_existing_target_mode_before_chmod(monkeypatch, tmp_path):
    # Codex-Befund (Checkpoint 3, Runde 6 P1): die Tempdatei wurde bisher
    # immer mit 0o666 (umask-maskiert) angelegt; der engere Zielmodus kam
    # erst nach dem Schreiben per chmod(). Reproduziert: Zieldatei 0600,
    # Tempdatei waehrend des Schreibens 0644 - sensible Inhalte waren so
    # kurzzeitig breiter lesbar als die Zieldatei erlaubt. Dieser Test
    # belegt per chmod()-Spy, dass die Tempdatei bereits VOR dem
    # expliziten chmod()-Aufruf hoechstens den Zielmodus besitzt.
    target = tmp_path / "secret.json"
    target.write_text("{}", encoding="utf-8")
    os.chmod(target, 0o600)

    observed = {}
    real_chmod = os.chmod

    def spy_chmod(path, mode):
        observed["mode_before_chmod"] = stat.S_IMODE(os.stat(path).st_mode)
        real_chmod(path, mode)

    monkeypatch.setattr(os, "chmod", spy_chmod)

    atomic_write_text(target, json.dumps({"updated": True}))

    assert observed["mode_before_chmod"] & ~0o600 == 0
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_first_created_registry_file_gets_umask_masked_default_mode(monkeypatch, tmp_path):
    # Codex-Befund (Checkpoint 3, Runde 5): "fehlt derzeit ein automatisierter
    # Test fuer den Modus einer erstmalig erzeugten Registry-Datei". Bei
    # Umask 0o022 muss eine neu angelegte mcp_registry.json mit 0o644 enden -
    # der Kernel maskiert 0o666 atomar beim Anlegen, nicht dieser Code.
    registry_path = _bind_registry(monkeypatch, tmp_path)
    assert not registry_path.exists()

    old_umask = os.umask(0o022)
    try:
        upsert_registry_entry(
            "demo",
            {
                "enabled": True,
                "transport": "http",
                "url": "http://demo:8000/mcp",
                "description": "Demo MCP",
                "version": "1.0.0",
            },
        )
    finally:
        os.umask(old_umask)

    assert stat.S_IMODE(registry_path.stat().st_mode) == 0o644
