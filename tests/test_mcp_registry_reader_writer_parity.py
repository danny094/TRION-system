import json

import pytest

from mcp.installer_registry import remove_registry_entry, upsert_registry_entry


def _bind_registry(monkeypatch, tmp_path):
    import mcp.config as mcp_config

    path = tmp_path / "mcp_registry.json"
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", path)
    return path


def test_writer_persists_only_custom_data_while_reader_projects_core(monkeypatch, tmp_path):
    path = _bind_registry(monkeypatch, tmp_path)
    upsert_registry_entry(
        "demo",
        {
            "enabled": True,
            "transport": "http",
            "url": "http://demo.invalid/mcp",
            "description": "Demo",
        },
    )

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert set(persisted) == {"demo"}
    assert "memory-mcp" not in persisted

    import mcp.config as mcp_config

    projected = mcp_config.get_all_mcps()
    assert set(projected) == {"memory-mcp", "demo"}
    assert projected["demo"] == persisted["demo"]

    remove_registry_entry("demo")
    assert json.loads(path.read_text(encoding="utf-8")) == {}


def test_source_failure_blocks_writer_without_rebuilding_defaults(monkeypatch, tmp_path):
    path = _bind_registry(monkeypatch, tmp_path)
    original = "{broken-json"
    path.write_text(original, encoding="utf-8")

    with pytest.raises(ValueError):
        upsert_registry_entry("demo", {"enabled": True})

    assert path.read_text(encoding="utf-8") == original


def test_core_id_cannot_enter_custom_registry(monkeypatch, tmp_path):
    path = _bind_registry(monkeypatch, tmp_path)

    with pytest.raises(ValueError):
        upsert_registry_entry("memory-mcp", {"enabled": False})
    assert not path.exists()

    path.write_text(json.dumps({"memory-mcp": {"enabled": False}}), encoding="utf-8")
    import mcp.config as mcp_config

    with pytest.raises(ValueError):
        mcp_config.get_all_mcps()
