"""P11.0 SP2 - Call-Site-Vertraege von Install/Update/Toggle (Codex Checkpoint 3).

Ergaenzt tests/test_tool_manifest_mirror_lifecycle.py (Registry-Writer-Ebene)
um Befunde, die dort nicht abgedeckt waren:

- P1.2: Update/Toggle muessen Custom-Config und Registry-Mirror als eine
  Transaktion behandeln; schlaegt der Registry-Schritt fehl, bleibt die alte
  Config erhalten statt mit dem alten Mirror auseinanderzulaufen. Runde 2:
  das Schreiben selbst (Config-Save und Rollback-Restore) muss atomar sein
  (Temp-Datei + os.replace), nicht nur logisch korrekt. Runde 3: die gesamte
  Transaktion (Config-Schreiben + Registry-Update + Rollback) muss unter
  einer gemeinsamen Sperre laufen, nicht nur der Registry-Schritt selbst;
  und der atomare Writer darf nach einem Schreibfehler keine Tempdatei
  zuruecklassen. Runde 4: der atomare Writer darf bestehende Dateirechte
  (z. B. Docker-Entrypoint-Gruppenrechte) nicht durch mkstemp()s 0600
  ueberschreiben.
- P2.2: Install (`installer_manifest._attach_tool_intents`) und Update/Toggle
  (`installer_manage_routes._preserve_tool_intents`) muessen denselben
  Mirror-Builder mit identischem Ergebnis verwenden, nicht nur "aehnlich".

Uninstall-/Rollback-Tests: test_mcp_installer_delete_mcp.py, test_mcp_installer_cleanup_failed_install.py (Checkpoint 4 P1).
"""
import json
import os
import stat
import threading
import time

import pytest

import mcp.installer_manage_config as installer_manage_config
from mcp.installer_common import InstallationError, save_custom_config
from mcp.installer_manage_routes import _apply_config_and_registry_update, _preserve_tool_intents
from mcp.installer_manifest import _attach_tool_intents


def test_apply_config_and_registry_update_restores_config_on_registry_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path))
    mcp_dir = tmp_path / "demo"
    mcp_dir.mkdir()
    original_config = {"enabled": True, "version": "1.0.0"}
    (mcp_dir / "mcp.json").write_text(json.dumps(original_config), encoding="utf-8")

    new_config = {"enabled": False, "version": "1.0.0"}
    # bundle_version ("9.9.9") passt nicht zur Manifest-version ("1.0.0") ->
    # installer_registry._assert_mirror_consistency() lehnt vor jedem
    # Registry-Schreibvorgang ab.
    bad_mirror = {
        "schema_version": 1,
        "source_sha256": "deadbeef",
        "bundle_version": "9.9.9",
        "tools": [],
    }
    normalized = {"version": "1.0.0", "tool_intents": bad_mirror}

    with pytest.raises(InstallationError):
        _apply_config_and_registry_update("demo", new_config, normalized)

    restored = json.loads((mcp_dir / "mcp.json").read_text(encoding="utf-8"))
    assert restored == original_config


def test_save_custom_config_write_failure_leaves_old_config_intact(monkeypatch, tmp_path):
    # Codex P1.2-Befund (Checkpoint 3, Runde 2): save_custom_config() schrieb
    # bisher direkt per write_text(); ein Fehler waehrend des Schreibens
    # konnte eine halb geschriebene Datei hinterlassen. save_custom_config()
    # nutzt jetzt installer_common.atomic_write_text() (Temp + os.replace) -
    # genau der Writer, den auch der Rollback-Pfad oben verwendet.
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path))
    mcp_dir = tmp_path / "demo"
    mcp_dir.mkdir()
    original_config = {"enabled": True, "version": "1.0.0"}
    (mcp_dir / "mcp.json").write_text(json.dumps(original_config), encoding="utf-8")

    import mcp.installer_common as installer_common

    def _boom(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(installer_common.os, "replace", _boom)

    with pytest.raises(OSError):
        save_custom_config("demo", {"enabled": False, "version": "1.0.0"})

    restored = json.loads((mcp_dir / "mcp.json").read_text(encoding="utf-8"))
    assert restored == original_config


def test_install_and_update_call_sites_use_the_same_mirror_builder(monkeypatch, tmp_path):
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path))
    tool_intents_payload = json.dumps(
        {"schema_version": 1, "tools": [{"name": "time_now", "description": "Return time."}]}
    )

    bundle_root = tmp_path / "extract_root"
    bundle_root.mkdir()
    (bundle_root / "tool_intents.json").write_text(tool_intents_payload, encoding="utf-8")
    install_normalized = {"version": "1.0.0"}
    _attach_tool_intents(install_normalized, bundle_root)

    custom_mcp_dir = tmp_path / "demo"
    custom_mcp_dir.mkdir()
    (custom_mcp_dir / "tool_intents.json").write_text(tool_intents_payload, encoding="utf-8")
    update_normalized = {"version": "1.0.0"}
    _preserve_tool_intents("demo", update_normalized)

    assert install_normalized["tool_intents"] == update_normalized["tool_intents"]


def test_apply_config_and_registry_update_serializes_full_transaction(monkeypatch, tmp_path):
    # Codex P1-Befund (Checkpoint 3, Runde 3): REGISTRY_LOCK sperrte zuvor nur
    # den Registry-Schritt selbst, nicht Config-Schreiben + Registry-Update +
    # Rollback gemeinsam. Ein paralleler Rollback konnte dadurch einen bereits
    # erfolgreichen Registry-Write einer anderen Anfrage durch die alte
    # Config widersprechen. Dieser Test belegt deterministisch ueber echte
    # Zeitfenster (nicht nur Code-Inspektion), dass der tatsaechliche
    # Schreibzeitpunkt (save_custom_config) zweier paralleler Aufrufe sich
    # nie ueberlappt.
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path))
    import mcp.config as mcp_config

    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", tmp_path / "mcp_registry.json")
    for n in ("a", "b"):
        d = tmp_path / n
        d.mkdir()
        (d / "mcp.json").write_text(json.dumps({"enabled": True, "version": "1.0.0"}), encoding="utf-8")

    real_save = installer_manage_config.save_custom_config
    events = []
    events_lock = threading.Lock()

    def tracking_save(name, config):
        start = time.monotonic()
        if name == "a":
            time.sleep(0.05)
        result = real_save(name, config)
        with events_lock:
            events.append((start, time.monotonic()))
        return result

    monkeypatch.setattr(installer_manage_config, "save_custom_config", tracking_save)

    threads = [
        threading.Thread(
            target=_apply_config_and_registry_update,
            args=(n, {"enabled": True, "version": "1.0.0"}, {"version": "1.0.0"}),
        )
        for n in ("a", "b")
    ]
    threads[0].start()
    time.sleep(0.01)
    threads[1].start()
    for t in threads:
        t.join()

    assert len(events) == 2
    (start_1, end_1), (start_2, end_2) = sorted(events)
    assert end_1 <= start_2


def test_atomic_write_text_leaves_no_tmp_file_after_replace_failure(monkeypatch, tmp_path):
    # Codex-Befund (Checkpoint 3, Runde 3 P1/P2): der alte feste Tempname
    # (`<datei>.tmp`) wurde bei einem os.replace()-Fehler nicht aufgeraeumt -
    # physischer Muell blieb liegen. atomic_write_text() nutzt jetzt einen
    # kollisionssicheren Tempnamen und raeumt im except-Block auf.
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path))
    mcp_dir = tmp_path / "demo"
    mcp_dir.mkdir()
    (mcp_dir / "mcp.json").write_text(json.dumps({"enabled": True}), encoding="utf-8")

    import mcp.installer_common as installer_common

    def _boom(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(installer_common.os, "replace", _boom)

    with pytest.raises(OSError):
        save_custom_config("demo", {"enabled": False})

    leftovers = [p.name for p in mcp_dir.iterdir() if ".tmp" in p.name]
    assert leftovers == []


def test_save_custom_config_preserves_existing_file_permissions(monkeypatch, tmp_path):
    # Codex-Befund (Checkpoint 3, Runde 4 P1): die Tempdatei wuerde ohne
    # expliziten chmod vor os.replace() nicht die Rechte einer bestehenden
    # mcp.json (z. B. vom Docker-Entrypoint mit Gruppenrechten angelegt)
    # uebernehmen. atomic_write_text() uebertraegt jetzt den Modus der
    # bestehenden Zieldatei auf die Tempdatei.
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path))
    mcp_dir = tmp_path / "demo"
    mcp_dir.mkdir()
    config_path = mcp_dir / "mcp.json"
    config_path.write_text(json.dumps({"enabled": True, "version": "1.0.0"}), encoding="utf-8")
    os.chmod(config_path, 0o664)

    save_custom_config("demo", {"enabled": False, "version": "1.0.0"})

    assert stat.S_IMODE(config_path.stat().st_mode) == 0o664
