"""P11.0 SP2 - Capability-Projektionsdrift im Registry-Mirror.

Eigene Datei statt Erweiterung von tests/test_tool_manifest_mirror_lifecycle.py,
da diese bereits an der 200-Zeilen-Grenze (Doc 07) liegt. Single
Responsibility: nur der Codex-Checkpoint-3-Runde-2-Befund, dass
`capability_complete`/`missing_capability_fields` vor dem Hashvergleich
entfernt, aber nie gegen den tatsaechlichen Toolinhalt zurueckgeprueft wurden.
"""
import json

import pytest

from mcp.installer_common import InstallationError
from mcp.installer_registry import upsert_registry_entry
from mcp.installer_tool_intents import build_tool_intent_mirror


def _bind_registry(monkeypatch, tmp_path):
    registry_path = tmp_path / "mcp_registry.json"
    import mcp.config as mcp_config

    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", registry_path)
    return registry_path


def _mirror_v2(tmp_path, subdir, tools, bundle_version="1.0.0"):
    bundle_dir = tmp_path / subdir
    bundle_dir.mkdir()
    path = bundle_dir / "tool_intents.json"
    path.write_text(json.dumps({"schema_version": 2, "tools": tools}), encoding="utf-8")
    return build_tool_intent_mirror(path, bundle_version=bundle_version)


def _config(version, mirror):
    return {
        "enabled": True,
        "transport": "http",
        "url": "http://demo:8000/mcp",
        "description": "Demo MCP",
        "version": version,
        "tool_intents": mirror,
    }


def test_build_tool_intent_mirror_marks_incomplete_v2_tool_fail_closed(tmp_path):
    # Beweist die Testvoraussetzung: ein Tool ohne alle P11-Pflichtfelder wird
    # von der echten SP1-Projektion als unvollstaendig markiert.
    mirror = _mirror_v2(tmp_path, "a", [{"name": "time_now", "description": "Return time."}])
    assert mirror["tools"][0]["capability_complete"] is False
    assert "missing_capability_fields" in mirror["tools"][0]


def test_upsert_registry_entry_rejects_capability_complete_flipped_after_build(monkeypatch, tmp_path):
    # Codex P1.1-Befund (Checkpoint 3, Runde 2): die Runde-1-Pruefung entfernte
    # capability_complete/missing_capability_fields vor dem Hash, verglich sie
    # aber nie gegen den tatsaechlichen Toolinhalt - ein unvollstaendiges
    # v2-Tool konnte nachtraeglich auf capability_complete=True gesetzt werden,
    # ohne den Hash zu beruehren.
    _bind_registry(monkeypatch, tmp_path)
    mirror = _mirror_v2(tmp_path, "a", [{"name": "time_now", "description": "Return time."}])

    mirror["tools"][0]["capability_complete"] = True
    mirror["tools"][0].pop("missing_capability_fields", None)

    with pytest.raises(InstallationError, match="projection"):
        upsert_registry_entry("demo", _config("1.0.0", mirror))


def test_upsert_registry_entry_rejects_missing_capability_fields_drift(monkeypatch, tmp_path):
    # Symmetrischer Fall: missing_capability_fields wird verkleinert, ohne
    # capability_complete anzupassen - muss ebenfalls als Drift erkannt werden.
    _bind_registry(monkeypatch, tmp_path)
    mirror = _mirror_v2(tmp_path, "a", [{"name": "time_now", "description": "Return time."}])
    real_missing = mirror["tools"][0]["missing_capability_fields"]
    assert len(real_missing) > 1

    mirror["tools"][0]["missing_capability_fields"] = real_missing[:1]

    with pytest.raises(InstallationError, match="projection"):
        upsert_registry_entry("demo", _config("1.0.0", mirror))
