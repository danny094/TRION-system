"""P11.0 SP3 - installer_manage_routes.delete_mcp() Uninstall-Lifecycle.

Herausgeloest aus tests/test_mcp_installer_route_wiring.py (Codex Checkpoint
4 P1: eigene Verantwortung, Doc 07s 200-Zeilen-Grenze). Rollback-Tests fuer
_cleanup_failed_install() liegen in
tests/test_mcp_installer_cleanup_failed_install.py.

Deckt ab:
- Reihenfolge bindend (P11.0-Plan): Mirror entfernen -> Hub reload -> Bundle
  entfernen.
- Codex Checkpoint 4 P0: ein manipuliertes Receipt (`owned_paths` zeigt auf
  ein fremdes Verzeichnis, oder `mcp_id` passt nicht) darf `shutil.rmtree()`
  nie auf einen Pfad ausserhalb des erwarteten Bundle-Verzeichnisses ansetzen.
- Codex Checkpoint 4 P1: kein `ignore_errors=True` mehr - Loeschfehler muessen
  sichtbar werden, Erfolg erst nach nachweislich verschwundenem Bundle-Pfad.
"""
import json

import pytest
from fastapi import HTTPException


def test_delete_mcp_removes_registry_then_reloads_hub_before_deleting_bundle(monkeypatch, tmp_path):
    # SP3 Lifecycle-Invariante (Uninstall-Reihenfolge): Mirror entfernen ->
    # Hub reload -> Bundle entfernen. Andernfalls haelt der Hub nach dem
    # Reload weiterhin einen Verweis auf ein bereits physisch entferntes
    # Bundle, oder ein paralleler Request liest ein halb geloeschtes Bundle,
    # dessen Registry-Eintrag noch da ist.
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path))
    mcp_dir = tmp_path / "demo"
    mcp_dir.mkdir()
    (mcp_dir / "mcp.json").write_text(json.dumps({"enabled": True, "version": "1.0.0"}), encoding="utf-8")
    receipt = {
        "mcp_id": "demo",
        "version": "1.0.0",
        "owned_paths": [str(mcp_dir)],
        "registry_paths": [],
        "runtime_created_paths": [],
    }
    (mcp_dir / ".trion-install.json").write_text(json.dumps(receipt), encoding="utf-8")

    import asyncio

    import mcp.installer_manage_routes as manage_routes

    order = []
    monkeypatch.setattr(
        manage_routes,
        "remove_registry_entry",
        lambda name: order.append(("remove_registry_entry", mcp_dir.exists())),
    )
    monkeypatch.setattr(
        manage_routes,
        "reload_hub_registry",
        lambda hub: order.append(("reload_hub_registry", mcp_dir.exists())) or "reload_registry",
    )

    real_rmtree = manage_routes.shutil.rmtree

    def tracking_rmtree(path):
        order.append(("rmtree", mcp_dir.exists()))
        real_rmtree(path)

    monkeypatch.setattr(manage_routes.shutil, "rmtree", tracking_rmtree)

    result = asyncio.run(manage_routes.delete_mcp("demo"))

    assert [step[0] for step in order] == ["remove_registry_entry", "reload_hub_registry", "rmtree"]
    # Zum Zeitpunkt von remove_registry_entry/reload_hub_registry existiert
    # das Bundle noch physisch - es wird erst als letzter Schritt entfernt.
    assert order[0][1] is True
    assert order[1][1] is True
    assert result == {"success": True, "deleted": "demo"}
    assert not mcp_dir.exists()


def test_delete_mcp_ignores_tampered_owned_paths_outside_the_bundle_dir(monkeypatch, tmp_path):
    # Codex Checkpoint 4 P0: ein manipuliertes Receipt (owned_paths zeigt auf
    # ein fremdes Verzeichnis) darf shutil.rmtree() nicht auf beliebige Pfade
    # ausserhalb des erwarteten Bundle-Verzeichnisses ansetzen.
    custom_mcps_dir = tmp_path / "custom_mcps"
    custom_mcps_dir.mkdir()
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(custom_mcps_dir))
    mcp_dir = custom_mcps_dir / "demo"
    mcp_dir.mkdir()
    (mcp_dir / "mcp.json").write_text(json.dumps({"enabled": True, "version": "1.0.0"}), encoding="utf-8")
    victim_dir = tmp_path / "victim"
    victim_dir.mkdir()
    (victim_dir / "important.txt").write_text("do not delete", encoding="utf-8")
    receipt = {
        "mcp_id": "demo",
        "version": "1.0.0",
        "owned_paths": [str(victim_dir)],  # manipuliert: zeigt ausserhalb des Bundles
        "registry_paths": [],
        "runtime_created_paths": [],
    }
    (mcp_dir / ".trion-install.json").write_text(json.dumps(receipt), encoding="utf-8")

    import asyncio

    import mcp.installer_manage_routes as manage_routes

    monkeypatch.setattr(manage_routes, "remove_registry_entry", lambda name: None)
    monkeypatch.setattr(manage_routes, "reload_hub_registry", lambda hub: "reload_registry")

    result = asyncio.run(manage_routes.delete_mcp("demo"))

    assert result == {"success": True, "deleted": "demo"}
    assert victim_dir.exists()
    assert (victim_dir / "important.txt").exists()
    assert not mcp_dir.exists()


def test_delete_mcp_rejects_receipt_with_mismatched_mcp_id(monkeypatch, tmp_path):
    # Codex Checkpoint 4 P0: ein Receipt mit fremder mcp_id (z.B. nach
    # Bundle-Vertauschung) muss die Loeschung komplett verweigern, bevor
    # Registry oder Hub angefasst werden.
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path))
    mcp_dir = tmp_path / "demo"
    mcp_dir.mkdir()
    (mcp_dir / "mcp.json").write_text(json.dumps({"enabled": True, "version": "1.0.0"}), encoding="utf-8")
    receipt = {
        "mcp_id": "other-mcp",
        "version": "1.0.0",
        "owned_paths": [str(mcp_dir)],
        "registry_paths": [],
        "runtime_created_paths": [],
    }
    (mcp_dir / ".trion-install.json").write_text(json.dumps(receipt), encoding="utf-8")

    import asyncio

    import mcp.installer_manage_routes as manage_routes

    called = []
    monkeypatch.setattr(manage_routes, "remove_registry_entry", lambda name: called.append(name))

    with pytest.raises(HTTPException):
        asyncio.run(manage_routes.delete_mcp("demo"))

    assert called == []
    assert mcp_dir.exists()


def test_delete_mcp_raises_when_bundle_directory_survives_deletion(monkeypatch, tmp_path):
    # Codex Checkpoint 4 P1: ignore_errors=True liess Loeschfehler bisher
    # verschwinden, Uninstall meldete Erfolg trotz weiterhin existierendem
    # Bundle. Jetzt: kein Erfolg ohne verifiziertes physisches Verschwinden.
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path))
    mcp_dir = tmp_path / "demo"
    mcp_dir.mkdir()
    (mcp_dir / "mcp.json").write_text(json.dumps({"enabled": True, "version": "1.0.0"}), encoding="utf-8")
    receipt = {
        "mcp_id": "demo",
        "version": "1.0.0",
        "owned_paths": [str(mcp_dir)],
        "registry_paths": [],
        "runtime_created_paths": [],
    }
    (mcp_dir / ".trion-install.json").write_text(json.dumps(receipt), encoding="utf-8")

    import asyncio

    import mcp.installer_manage_routes as manage_routes

    monkeypatch.setattr(manage_routes, "remove_registry_entry", lambda name: None)
    monkeypatch.setattr(manage_routes, "reload_hub_registry", lambda hub: "reload_registry")
    monkeypatch.setattr(manage_routes.shutil, "rmtree", lambda path: None)  # simuliert Loeschfehler

    with pytest.raises(HTTPException):
        asyncio.run(manage_routes.delete_mcp("demo"))

    assert mcp_dir.exists()
