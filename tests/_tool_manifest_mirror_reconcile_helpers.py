"""Gemeinsame Test-Helfer fuer den P11.0 SP3 Reconciler.

Kein `test_`-Praefix - wird von pytest nicht als Testmodul eingesammelt.
Ausgelagert aus tests/test_tool_manifest_mirror_reconcile.py (Codex
Checkpoint 4 P1: Testdateien unterliegen Doc 07s 200-Zeilen-Grenze wie
jede andere Datei, keine Ausnahme), damit beide Testdateien
(test_tool_manifest_mirror_reconcile.py fuer DECIDE-2-Ownership-Faelle,
test_tool_manifest_mirror_reconcile_repair.py fuer Mirror-Reparatur-Faelle)
dieselben Fixtures ohne Duplikation nutzen.
"""
import json

from mcp.installer_receipt import RECEIPT_FILE


def _bind_registry(monkeypatch, tmp_path, registry: dict):
    import mcp.config as mcp_config

    registry_path = tmp_path / "mcp_registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", registry_path)
    return registry_path


def _bind_custom_mcps_dir(monkeypatch, tmp_path):
    # custom_mcps_dir() lebt in mcp.installer_paths (Codex Checkpoint 4 P0,
    # 2. Runde: installer_common.py wurde aufgeteilt, siehe installer_paths.py).
    # installer_reconcile.py importiert custom_mcp_dir() als gebundenen Namen
    # aus installer_common - dieser ruft intern aber das custom_mcps_dir()
    # seines EIGENEN Moduls (installer_paths) auf, nicht das von
    # installer_common. Patchen muss daher an der tatsaechlichen Quelle
    # ansetzen, sonst greift der Patch nie.
    import mcp.installer_paths as installer_paths

    custom_dir = tmp_path / "custom_mcps"
    custom_dir.mkdir()
    monkeypatch.setattr(installer_paths, "custom_mcps_dir", lambda: custom_dir)
    return custom_dir


def _write_bundle(custom_dir, name: str, tools: list, with_receipt: bool = True):
    bundle_dir = custom_dir / name
    bundle_dir.mkdir()
    (bundle_dir / "tool_intents.json").write_text(
        json.dumps({"schema_version": 1, "tools": tools}), encoding="utf-8"
    )
    if with_receipt:
        (bundle_dir / RECEIPT_FILE).write_text("{}", encoding="utf-8")
    return bundle_dir


def _registry_entry(version="1.0.0", managed_by=None, tool_intents=None):
    entry = {
        "enabled": True,
        "transport": "http",
        "url": "http://demo:8000/mcp",
        "description": "Demo",
        "display_name": "Demo",
        "version": version,
        "schema_version": 0,
        "entry": {},
        "ui": {},
        "plugin": None,
        "install": {},
        "tool_intents": tool_intents,
    }
    if managed_by is not None:
        entry["managed_by"] = managed_by
    return entry
