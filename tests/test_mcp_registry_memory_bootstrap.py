"""Memory-MCP-Bootstrap-Vertrag in mcp/config.py.

Ausgelagert aus tests/test_mcp_registry_runtime.py (P11.0 SP0, Codex-Befund:
225 Zeilen ueberschritten Doc 07s 200-Zeilen-Grenze). Memory-MCP durchlaeuft
nie Install/Update/Uninstall und hat daher keinen Registry-Mirror-Eintrag -
dieser Sonderfall wird erst in SP3 final geloest (siehe P11.0-Plan, Ist-Stand).
"""
import json

import pytest


def test_config_includes_memory_mcp_default_when_registry_file_missing(monkeypatch, tmp_path):
    import mcp.config as mcp_config

    registry_path = tmp_path / "missing_registry.json"
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", registry_path)
    monkeypatch.setenv("MCP_BASE", "http://trion-memory:8081")

    payload = mcp_config.get_enabled_mcps()

    assert "memory-mcp" in payload
    assert payload["memory-mcp"]["enabled"] is True
    assert payload["memory-mcp"]["transport"] == "http"
    assert payload["memory-mcp"]["url"] == "http://trion-memory:8081/mcp"
    assert payload["memory-mcp"]["tool_intents"]["tools"]


def test_config_rejects_memory_mcp_transport_override_as_core_custom_collision(
    monkeypatch, tmp_path
):
    import mcp.config as mcp_config

    registry_path = tmp_path / "mcp_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "memory-mcp": {
                    "enabled": True,
                    "transport": "http",
                    "url": "http://override-memory:9000/mcp",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", registry_path)

    with pytest.raises(ValueError):
        mcp_config.get_all_mcps()


def test_config_rejects_memory_mcp_tool_intents_as_core_custom_collision(
    monkeypatch, tmp_path
):
    import mcp.config as mcp_config

    registry_path = tmp_path / "mcp_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "memory-mcp": {
                    "enabled": True,
                    "transport": "http",
                    "url": "http://override-memory:9000/mcp",
                    "tool_intents": {
                        "schema_version": 1,
                        "tools": [
                            {
                                "name": "totally_fake_tool",
                                "description": "Manually injected via registry file",
                            }
                        ],
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", registry_path)

    with pytest.raises(ValueError):
        mcp_config.get_all_mcps()
