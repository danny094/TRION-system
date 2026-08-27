import asyncio
import importlib.util
import json
from pathlib import Path

from mcp.tool_result_contracts import (
    MCPResultPresence as Presence,
    MCPToolCallStatus as ToolStatus,
    MCPToolResultEnvelope,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "adapters" / "admin-api" / "protocol_routes.py"


def _load_protocol_routes():
    spec = importlib.util.spec_from_file_location(
        "trion_protocol_routes_tool_result_test",
        MODULE_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Hub:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def initialize(self):
        return None

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return self.results[len(self.calls) - 1]


def _body(response):
    return json.loads(response.body.decode("utf-8"))


def test_protocol_merge_counts_only_success_and_preserves_envelopes(
    monkeypatch,
    tmp_path,
):
    protocol_routes = _load_protocol_routes()
    date = "2026-08-03"
    entries = "\n\n".join(
        f"## 09:0{index}\nentry-{index}" for index in range(4)
    )
    (tmp_path / f"{date}.md").write_text(f"# Tagesprotokoll {date}\n\n{entries}\n")
    protocol_routes.PROTOCOL_DIR = tmp_path
    protocol_routes.STATUS_FILE = tmp_path / ".protocol_status.json"

    results = (
        MCPToolResultEnvelope(
            ToolStatus.SUCCESS,
            structured_content_presence=Presence.VALUE,
            structured_content={"node_id": "node-1"},
            is_error_presence=Presence.VALUE,
            is_error=False,
        ),
        MCPToolResultEnvelope(
            ToolStatus.TOOL_FAILURE,
            content_presence=Presence.EMPTY,
            content=(),
            structured_content_presence=Presence.EMPTY,
            structured_content={},
            is_error_presence=Presence.VALUE,
            is_error=True,
        ),
        MCPToolResultEnvelope(
            ToolStatus.PROTOCOL_FAILURE,
            protocol_error={"code": -32603, "message": "display only"},
        ),
        MCPToolResultEnvelope(
            ToolStatus.TRANSPORT_FAILURE,
            transport_diagnostic="display only",
        ),
    )
    hub = _Hub(results)
    monkeypatch.setattr("mcp.hub.get_hub", lambda: hub)

    response = asyncio.run(protocol_routes.protocol_merge(date))

    assert response.status_code == 200
    assert _body(response)["entries_merged"] == 1
    assert len(hub.calls) == 4
    assert tuple(hub.results) == results
    assert hub.results[1].content_presence is Presence.EMPTY
    assert hub.results[2].protocol_error["message"] == "display only"
    assert hub.results[3].transport_diagnostic == "display only"
