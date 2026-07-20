"""P11.0 SP3 - mcp.installer_reconcile.reconcile_tool_manifest_mirrors().

DECIDE-2-Ownership-Scope-Faelle (siehe tests/test_tool_manifest_mirror_reconcile_repair.py
fuer die Mirror-Reparatur-Faelle - Codex Checkpoint 4 P1: getrennt, weil eine
gemeinsame Datei Doc 07s 200-Zeilen-Grenze ueberschritten haette und beide
Cluster fachlich unterschiedliche Verantwortung haben):

- ein Eintrag wird nur dann komplett entfernt, wenn `managed_by ==
  MANAGED_BY_INSTALLER` bewiesen ist. Fehlen Bundle, Receipt UND Marker
  gleichzeitig, wird nicht geraten/geloescht, sondern als `unresolved`
  gemeldet. Core-/Memory-Eintraege werden nie angefasst.
"""
import json

from mcp.config import core_mcp_names
from mcp.installer_reconcile import reconcile_tool_manifest_mirrors
from mcp.installer_registry import MANAGED_BY_INSTALLER
from tests._tool_manifest_mirror_reconcile_helpers import (
    _bind_custom_mcps_dir,
    _bind_registry,
    _registry_entry,
    _write_bundle,
)


def test_reconcile_backfills_marker_and_refreshes_mirror_for_installer_owned_entry(
    monkeypatch, tmp_path
):
    custom_dir = _bind_custom_mcps_dir(monkeypatch, tmp_path)
    _write_bundle(custom_dir, "alpha", [{"name": "alpha_tool", "description": "Alpha."}])
    registry_path = _bind_registry(
        monkeypatch, tmp_path, {"alpha": _registry_entry(tool_intents=None)}
    )

    result = reconcile_tool_manifest_mirrors()

    assert result == {
        "changed": True,
        "repaired": ["alpha"],
        "removed": [],
        "unresolved": [],
    }
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert payload["alpha"]["managed_by"] == MANAGED_BY_INSTALLER
    assert payload["alpha"]["tool_intents"]["tools"][0]["name"] == "alpha_tool"


def test_reconcile_removes_orphaned_installer_owned_entry_when_bundle_dir_gone(
    monkeypatch, tmp_path
):
    _bind_custom_mcps_dir(monkeypatch, tmp_path)  # leer: kein "beta"-Bundle-Verzeichnis
    registry_path = _bind_registry(
        monkeypatch,
        tmp_path,
        {"beta": _registry_entry(managed_by=MANAGED_BY_INSTALLER)},
    )

    result = reconcile_tool_manifest_mirrors()

    assert result == {
        "changed": True,
        "repaired": [],
        "removed": ["beta"],
        "unresolved": [],
    }
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert "beta" not in payload


def test_reconcile_reports_unresolved_when_ownership_not_provable(monkeypatch, tmp_path):
    _bind_custom_mcps_dir(monkeypatch, tmp_path)  # kein "gamma"-Bundle, kein Receipt
    registry_path = _bind_registry(
        monkeypatch, tmp_path, {"gamma": _registry_entry(managed_by=None)}
    )

    result = reconcile_tool_manifest_mirrors()

    assert result == {
        "changed": False,
        "repaired": [],
        "removed": [],
        "unresolved": ["gamma"],
    }
    # Codex DECIDE 2: nicht raten, nicht loeschen - der Eintrag bleibt
    # unveraendert liegen, bis das Eigentum extern geklaert ist.
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert "gamma" in payload
    assert "managed_by" not in payload["gamma"]


def test_reconcile_excludes_core_mcp_entries(monkeypatch, tmp_path):
    _bind_custom_mcps_dir(monkeypatch, tmp_path)
    missing_registry = tmp_path / "missing_registry.json"
    import mcp.config as mcp_config

    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", missing_registry)

    assert "memory-mcp" in core_mcp_names()

    result = reconcile_tool_manifest_mirrors()

    assert result == {"changed": False, "repaired": [], "removed": [], "unresolved": []}
