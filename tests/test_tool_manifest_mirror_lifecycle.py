"""P11.0 SP2 - atomare Mirror-Persistenz in mcp_registry.json.

Testet den von Codex bestaetigten SP2-Vertrag (kein Downgrade-/Semver-Check):
Vorab-Konsistenzpruefung des frisch gebauten Mirrors vor dem atomaren
Schreiben, danach vollstaendiger Ersatz - nie ein partieller Merge mit dem
alten Mirror.
"""
import json
import os
import threading
import time

import pytest

from mcp.installer_common import InstallationError
from mcp.installer_registry import remove_registry_entry, upsert_registry_entry
from mcp.installer_tool_intents import build_tool_intent_mirror


def _bind_registry(monkeypatch, tmp_path):
    registry_path = tmp_path / "mcp_registry.json"
    import mcp.config as mcp_config

    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", registry_path)
    return registry_path


def _mirror(tmp_path, subdir, tools, bundle_version="1.0.0"):
    bundle_dir = tmp_path / subdir
    bundle_dir.mkdir()
    path = bundle_dir / "tool_intents.json"
    path.write_text(json.dumps({"schema_version": 1, "tools": tools}), encoding="utf-8")
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


def test_upsert_registry_entry_same_version_same_hash_is_allowed(monkeypatch, tmp_path):
    registry_path = _bind_registry(monkeypatch, tmp_path)
    mirror = _mirror(tmp_path, "a", [{"name": "time_now", "description": "Return time."}])

    upsert_registry_entry("demo", _config("1.0.0", mirror))
    upsert_registry_entry("demo", _config("1.0.0", mirror))

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert payload["demo"]["tool_intents"]["source_sha256"] == mirror["source_sha256"]


def test_upsert_registry_entry_same_version_new_hash_replaces_fully(monkeypatch, tmp_path):
    registry_path = _bind_registry(monkeypatch, tmp_path)
    old_mirror = _mirror(tmp_path, "a", [{"name": "time_now", "description": "Return time."}])
    upsert_registry_entry("demo", _config("1.0.0", old_mirror))

    new_mirror = _mirror(
        tmp_path, "b", [{"name": "time_now", "description": "Return current time."}]
    )
    upsert_registry_entry("demo", _config("1.0.0", new_mirror))

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert payload["demo"]["tool_intents"]["source_sha256"] == new_mirror["source_sha256"]
    assert payload["demo"]["tool_intents"]["source_sha256"] != old_mirror["source_sha256"]


def test_upsert_registry_entry_other_version_new_hash_replaces_fully(monkeypatch, tmp_path):
    registry_path = _bind_registry(monkeypatch, tmp_path)
    old_mirror = _mirror(tmp_path, "a", [{"name": "time_now", "description": "Return time."}])
    upsert_registry_entry("demo", _config("1.0.0", old_mirror))

    new_mirror = _mirror(
        tmp_path, "b", [{"name": "time_now", "description": "v2."}], bundle_version="2.0.0"
    )
    upsert_registry_entry("demo", _config("2.0.0", new_mirror))

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert payload["demo"]["version"] == "2.0.0"
    assert payload["demo"]["tool_intents"]["bundle_version"] == "2.0.0"


def test_upsert_registry_entry_update_does_not_merge_with_old_mirror_tools(monkeypatch, tmp_path):
    registry_path = _bind_registry(monkeypatch, tmp_path)
    old_mirror = _mirror(tmp_path, "a", [{"name": "old_tool", "description": "Old."}])
    upsert_registry_entry("demo", _config("1.0.0", old_mirror))

    new_mirror = _mirror(
        tmp_path, "b", [{"name": "new_tool", "description": "New."}], bundle_version="1.1.0"
    )
    upsert_registry_entry("demo", _config("1.1.0", new_mirror))

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    tool_names = {tool["name"] for tool in payload["demo"]["tool_intents"]["tools"]}
    assert tool_names == {"new_tool"}


def test_upsert_registry_entry_rejects_mirror_version_mismatch(monkeypatch, tmp_path):
    _bind_registry(monkeypatch, tmp_path)
    mirror = _mirror(tmp_path, "a", [{"name": "time_now", "description": "Return time."}])

    with pytest.raises(InstallationError, match="bundle_version"):
        upsert_registry_entry("demo", _config("9.9.9", mirror))


def test_upsert_registry_entry_rejects_tool_intent_meta_drift_from_header(monkeypatch, tmp_path):
    _bind_registry(monkeypatch, tmp_path)
    mirror = _mirror(tmp_path, "a", [{"name": "time_now", "description": "Return time."}])
    mirror["tools"][0]["tool_intent_meta"]["bundle_version"] = "stale"

    with pytest.raises(InstallationError, match="tool_intent_meta"):
        upsert_registry_entry("demo", _config("1.0.0", mirror))


def test_upsert_registry_entry_rejects_tool_projection_tampered_after_build(monkeypatch, tmp_path):
    # Codex P1.1-Befund (Checkpoint 3): eine nachtraeglich am Mirror
    # manipulierte Toolbeschreibung muss erkannt werden, auch wenn Header und
    # tool_intent_meta unangetastet bleiben - source_sha256 muss zur
    # tatsaechlichen Toolprojektion passen.
    _bind_registry(monkeypatch, tmp_path)
    mirror = _mirror(tmp_path, "a", [{"name": "time_now", "description": "Return time."}])
    mirror["tools"][0]["description"] = "Return whatever the attacker wants."

    with pytest.raises(InstallationError, match="source_sha256"):
        upsert_registry_entry("demo", _config("1.0.0", mirror))


def test_upsert_registry_entry_write_failure_leaves_old_registry_intact(monkeypatch, tmp_path):
    registry_path = _bind_registry(monkeypatch, tmp_path)
    registry_path.write_text(json.dumps({"existing": {"enabled": True}}), encoding="utf-8")

    def _boom(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", _boom)

    with pytest.raises(OSError):
        upsert_registry_entry("demo", _config("1.0.0", {}))

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert payload == {"existing": {"enabled": True}}


def test_upsert_registry_entry_concurrent_writes_do_not_lose_updates(monkeypatch, tmp_path):
    registry_path = _bind_registry(monkeypatch, tmp_path)
    import mcp.installer_registry as installer_registry

    original_write = installer_registry._write_registry

    def slow_write(registry):
        # Kuenstliche Verzoegerung innerhalb des gelockten Abschnitts: weitet
        # das Race-Fenster, damit ein versehentlich entferntes Lock dieses
        # Verfahren zuverlaessig zum Scheitern (verlorene Updates) bringt.
        time.sleep(0.01)
        original_write(registry)

    monkeypatch.setattr(installer_registry, "_write_registry", slow_write)

    def make_config(n):
        return {
            "enabled": True,
            "transport": "http",
            "url": f"http://mcp{n}:8000/mcp",
            "description": f"mcp{n}",
            "version": "1.0.0",
        }

    threads = [
        threading.Thread(target=upsert_registry_entry, args=(f"mcp{i}", make_config(i)))
        for i in range(6)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    # "memory-mcp" kommt aus mcp.config._default_mcps() und ist kein Resultat
    # dieses Tests; relevant ist nur, dass keiner der parallel geschriebenen
    # Eintraege durch eine verlorene Aktualisierung verschwunden ist.
    written = {name for name in payload if name != "memory-mcp"}
    assert written == {f"mcp{i}" for i in range(6)}


def test_remove_registry_entry_removes_existing_entry(monkeypatch, tmp_path):
    registry_path = _bind_registry(monkeypatch, tmp_path)
    upsert_registry_entry("demo", _config("1.0.0", {}))

    remove_registry_entry("demo")

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert "demo" not in payload
