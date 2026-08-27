import importlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = ROOT / "mcp-servers" / "filesystem"
SERVERS_ROOT = BUNDLE_ROOT.parent


def _module(name: str):
    assert BUNDLE_ROOT.is_dir(), "R6 Filesystem MCP product slice is absent"
    if str(SERVERS_ROOT) not in sys.path:
        sys.path.insert(0, str(SERVERS_ROOT))
    return importlib.import_module(f"filesystem.{name}")


def test_bundle_manifest_is_installer_compatible_stdio():
    assert BUNDLE_ROOT.is_dir(), "R6 Filesystem MCP product slice is absent"
    manifest = json.loads((BUNDLE_ROOT / "mcp.json").read_text(encoding="utf-8"))

    assert manifest == {
        "schema_version": 1,
        "id": "filesystem",
        "display_name": "TRION Home Filesystem",
        "version": "1.0.0",
        "description": "Read-only bounded access to files in TRION Home.",
        "transport": "stdio",
        "entry": {"type": "stdio", "command": ".venv/bin/python server.py"},
        "install": {"runtime": {"kind": "venv"}},
    }


def test_tool_intents_match_live_tool_contracts():
    server = _module("server")
    intents = json.loads((BUNDLE_ROOT / "tool_intents.json").read_text(encoding="utf-8"))
    live = {tool["name"]: tool for tool in server.TOOLS}

    assert intents["schema_version"] == 2
    assert {tool["name"] for tool in intents["tools"]} == set(live)
    for tool in intents["tools"]:
        assert tool["domain"] == "files"
        assert tool["risk"] == "read_only"
        assert tool["target_scopes"] == ["assistant_home"]
        assert tool["evidence_types"] == ["file_context"]
        assert tool["freshness_support"] == "live_only"
        assert tool["tool_role"] == "primary"
        assert tool["output_schema"] == "mcp_output_schema"
        assert tool["can_answer_directly"] is True
        assert tool["requires"] == live[tool["name"]]["inputSchema"].get("required", [])


def test_stdio_entry_exposes_exact_protocol_and_tools():
    server = _module("server")

    initialized = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    listed = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    assert initialized["result"]["protocolVersion"] == "2024-11-05"
    assert initialized["result"]["serverInfo"]["name"] == "filesystem"
    assert listed["result"]["tools"] == server.TOOLS


def test_manifest_command_runs_the_committed_stdio_entry():
    request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}) + "\n"
    result = subprocess.run(
        [sys.executable, "server.py"],
        cwd=BUNDLE_ROOT,
        input=request,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout)
    assert response["result"]["protocolVersion"] == "2024-11-05"
