import io
import json
import tarfile
import zipfile

import pytest

from mcp.installer_manage_routes import (
    _preserve_runtime_context,
    _validate_manifest_identity,
)
from mcp.installer_manifest import extract_archive, load_tool_intents, normalize_manifest_payload
def test_extract_archive_supports_mcp_json_zip(tmp_path):
    payload = {
        "schema_version": 1,
        "id": "time-mcp-test",
        "display_name": "Time MCP",
        "version": "1.2.3",
        "description": "Clock access",
        "transport": "http",
        "entry": {"type": "remote_url", "url": "http://time:8000/mcp"},
        "ui": {"icon": "assets/icon.svg"},
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr("mcp.json", json.dumps(payload))
        bundle.writestr(
            "tool_intents.json",
            json.dumps(
                {
                    "schema_version": 1,
                    "tools": [
                        {
                            "name": "time_now",
                            "description": "Return current UTC time and date.",
                            "examples": ["Wie viel Uhr ist es?"],
                            "keywords": ["uhrzeit", "time"],
                        }
                    ],
                }
            ),
        )

    extract_root, manifest = extract_archive("time-mcp-test.zip", buffer.getvalue(), tmp_dir=tmp_path)

    assert extract_root.name == "mcp_extract"
    assert manifest["id"] == "time-mcp-test"
    assert manifest["display_name"] == "Time MCP"
    assert manifest["version"] == "1.2.3"
    assert manifest["url"] == "http://time:8000/mcp"
    assert manifest["ui"]["icon"] == "assets/icon.svg"
    assert manifest["tool_intents"]["tools"][0]["name"] == "time_now"
def test_extract_archive_supports_legacy_tar_gz(tmp_path):
    payload = {
        "tier": "simple",
        "name": "legacy-time",
        "url": "http://legacy-time:8000/mcp",
        "description": "Legacy clock access",
    }
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as bundle:
        raw = json.dumps(payload).encode("utf-8")
        info = tarfile.TarInfo(name="config.json")
        info.size = len(raw)
        bundle.addfile(info, io.BytesIO(raw))

    _, manifest = extract_archive("legacy-time.tar.gz", buffer.getvalue(), tmp_dir=tmp_path)

    assert manifest["id"] == "legacy-time"
    assert manifest["display_name"] == "legacy-time"
    assert manifest["manifest_format"] == "config.json"
    assert manifest["url"] == "http://legacy-time:8000/mcp"
def test_extract_archive_supports_stdio_mcp_manifest_zip(tmp_path):
    payload = {
        "schema_version": 1,
        "id": "time-mcp-stdio",
        "display_name": "Time MCP STDIO",
        "version": "1.0.0",
        "description": "Clock access over stdio",
        "transport": "stdio",
        "entry": {"type": "stdio", "command": ".venv/bin/python server.py"},
        "install": {"runtime": {"kind": "venv"}},
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr("mcp.json", json.dumps(payload))

    _, manifest = extract_archive("time-mcp-stdio.zip", buffer.getvalue(), tmp_dir=tmp_path)

    assert manifest["id"] == "time-mcp-stdio"
    assert manifest["transport"] == "stdio"
    assert manifest["command"] == ".venv/bin/python server.py"
def test_extract_archive_ignores_macosx_wrapper_content(tmp_path):
    payload = {
        "schema_version": 1,
        "id": "time-mcp-macos",
        "display_name": "Time MCP",
        "version": "1.0.0",
        "description": "Clock access",
        "transport": "http",
        "entry": {"type": "remote_url", "url": "http://time:8000/mcp"},
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr("__MACOSX/._time_mcp_bundle", "")
        bundle.writestr("time_mcp_bundle/.DS_Store", "")
        bundle.writestr("time_mcp_bundle/mcp.json", json.dumps(payload))

    extract_root, manifest = extract_archive("time-mcp-macos.zip", buffer.getvalue(), tmp_dir=tmp_path)

    assert extract_root.name == "time_mcp_bundle"
    assert manifest["id"] == "time-mcp-macos"
def test_normalize_manifest_payload_supports_settings_update_for_mcp_json():
    payload = {
        "schema_version": 1,
        "id": "time-mcp-stdio",
        "display_name": "Time MCP STDIO",
        "version": "1.0.1",
        "description": "Clock access over stdio",
        "transport": "stdio",
        "entry": {"type": "stdio", "command": ".venv/bin/python server.py"},
        "ui": {"settings": {"enabled": True, "mode": "config"}},
    }

    manifest = normalize_manifest_payload("mcp.json", payload)
    _validate_manifest_identity("time-mcp-stdio", manifest, "mcp.json")
    _preserve_runtime_context("time-mcp-stdio", manifest)

    assert manifest["command"] == ".venv/bin/python server.py"
    assert manifest["cwd"] == "/app/custom_mcps/time-mcp-stdio"
def test_validate_manifest_identity_rejects_id_changes():
    manifest = {
        "id": "other-mcp",
        "entry": {"type": "remote_url", "url": "http://other:8000/mcp"},
    }

    with pytest.raises(ValueError, match="must stay 'time-mcp-stdio'"):
        _validate_manifest_identity("time-mcp-stdio", manifest, "mcp.json")
def test_normalize_manifest_payload_preserves_stdio_runtime_for_toggle():
    config = {
        "schema_version": 1,
        "id": "time-mcp-toggle",
        "display_name": "Time MCP Toggle",
        "version": "1.0.0",
        "description": "Clock access over stdio",
        "enabled": False,
        "transport": "stdio",
        "entry": {"type": "stdio", "command": ".venv/bin/python server.py"},
        "ui": {"settings": {"enabled": True, "mode": "config"}},
    }

    manifest = normalize_manifest_payload("mcp.json", config)
    _validate_manifest_identity("time-mcp-toggle", manifest, "mcp.json")
    _preserve_runtime_context("time-mcp-toggle", manifest)

    assert manifest["enabled"] is False
    assert manifest["command"] == ".venv/bin/python server.py"
    assert manifest["cwd"] == "/app/custom_mcps/time-mcp-toggle"
def test_load_tool_intents_validates_required_fields(tmp_path):
    payload = {
        "schema_version": 1,
        "tools": [{"name": "time_now", "description": "Return time.", "examples": ["Wie viel Uhr ist es?"]}],
    }
    path = tmp_path / "tool_intents.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = load_tool_intents(path)
    assert loaded["schema_version"] == 1
    assert loaded["tools"][0]["keywords"] == []
def test_load_tool_intents_preserves_capability_fields(tmp_path):
    payload = {
        "schema_version": 1,
        "tools": [
            {
                "name": "container_inspect",
                "description": "Inspect a container.",
                "domain": "container_runtime",
                "operation": "inspect",
                "supports_entities": ["container"],
                "evidence_types": ["runtime_metadata", "home_scope"],
                "requires": ["container_id_or_name"],
                "risk": "read_only",
                "target_scopes": ["runtime_state"],
                "tool_role": "primary",
                "can_answer_directly": True,
            }
        ],
    }
    path = tmp_path / "tool_intents.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = load_tool_intents(path)
    tool = loaded["tools"][0]
    assert tool["domain"] == "container_runtime"
    assert tool["operation"] == "inspect"
    assert tool["supports_entities"] == ["container"]
    assert tool["evidence_types"] == ["runtime_metadata", "home_scope"]
    assert tool["requires"] == ["container_id_or_name"]
    assert tool["risk"] == "read_only"
    assert tool["target_scopes"] == ["runtime_state"]
    assert tool["tool_role"] == "primary"
    assert tool["can_answer_directly"] is True
