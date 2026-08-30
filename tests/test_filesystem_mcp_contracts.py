import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = ROOT / "mcp-servers" / "filesystem"
SERVERS_ROOT = BUNDLE_ROOT.parent


def _module(name: str):
    assert BUNDLE_ROOT.is_dir(), "R6 Filesystem MCP product slice is absent"
    if str(SERVERS_ROOT) not in sys.path:
        sys.path.insert(0, str(SERVERS_ROOT))
    return importlib.import_module(f"filesystem.{name}")


def test_contract_limits_reject_values_above_hard_caps():
    contracts = _module("contracts")

    assert contracts.bounded_value(None, default=100, hard_cap=500, field="max_entries") == 100
    assert contracts.bounded_value(500, default=100, hard_cap=500, field="max_entries") == 500
    with pytest.raises(contracts.FilesystemFailure) as failure:
        contracts.bounded_value(501, default=100, hard_cap=500, field="max_entries")
    assert failure.value.code == "LIMIT_EXCEEDED"


def test_directory_name_scan_stops_at_hard_budget(monkeypatch):
    listing = _module("listing")
    consumed = 0

    def guarded_entries():
        nonlocal consumed
        for value in ("c", "b", "a", "z", "must-not-be-read"):
            consumed += 1
            assert consumed <= 4
            yield SimpleNamespace(name=value)

    class GuardedScan:
        def __enter__(self):
            return guarded_entries()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(listing.os, "scandir", lambda _fd: GuardedScan())

    names, truncated = listing._bounded_names(7, 3)

    assert names == ["a", "b", "c"]
    assert truncated is True
    assert consumed == 4


def test_error_envelope_keeps_typed_status_authoritative(tmp_path):
    server = _module("server")

    response = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": "req-1",
            "method": "tools/call",
            "params": {"name": "filesystem_read", "arguments": {}},
        },
        root=tmp_path,
    )

    result = response["result"]
    assert result["isError"] is True
    assert result["structuredContent"]["error"]["code"] == "MALFORMED_REQUEST"
    assert result["content"][0]["type"] == "text"

    for tool in server.TOOLS:
        Draft202012Validator(tool["outputSchema"]).validate(result["structuredContent"])


def test_live_tools_publish_input_and_output_schemas():
    contracts = _module("contracts")
    server = _module("server")

    tools = {tool["name"]: tool for tool in server.TOOLS}
    assert set(tools) == {
        "filesystem_list",
        "filesystem_search",
        "filesystem_metadata",
        "filesystem_read",
    }
    assert tools["filesystem_search"]["inputSchema"]["required"] == ["query"]
    assert tools["filesystem_metadata"]["inputSchema"]["required"] == ["relative_path"]
    assert tools["filesystem_read"]["inputSchema"]["required"] == ["relative_path"]
    assert tools["filesystem_list"]["inputSchema"]["properties"]["max_entries"]["maximum"] == contracts.LIST_MAX_ENTRIES
    assert tools["filesystem_list"]["inputSchema"]["properties"]["max_depth"]["maximum"] == contracts.LIST_MAX_DEPTH
    assert tools["filesystem_search"]["inputSchema"]["properties"]["max_results"]["maximum"] == contracts.SEARCH_MAX_RESULTS
    assert tools["filesystem_search"]["inputSchema"]["properties"]["max_depth"]["maximum"] == contracts.SEARCH_MAX_DEPTH
    assert tools["filesystem_read"]["inputSchema"]["properties"]["max_bytes"]["maximum"] == contracts.READ_MAX_BYTES
    assert all(tool["outputSchema"]["type"] == "object" for tool in tools.values())
