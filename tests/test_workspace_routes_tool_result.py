import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

from mcp.tool_result_contracts import (
    MCPResultPresence as Presence,
    MCPToolCallStatus as ToolStatus,
    MCPToolResultEnvelope,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "adapters" / "admin-api" / "workspace_routes.py"


def _load_workspace_routes():
    spec = importlib.util.spec_from_file_location(
        "trion_workspace_routes_tool_result_test",
        MODULE_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Hub:
    def __init__(self, result):
        self.result = result

    def initialize(self):
        return None

    def call_tool(self, _name, _arguments):
        return self.result


def _body(response):
    return json.loads(response.body.decode("utf-8"))


def _run_list(monkeypatch, result):
    workspace_routes = _load_workspace_routes()
    hub = _Hub(result)
    monkeypatch.setattr("mcp.hub.get_hub", lambda: hub)
    response = asyncio.run(workspace_routes.workspace_list())
    return response, hub


@pytest.mark.parametrize(
    ("presence", "structured_content", "expected_entries"),
    [
        (Presence.MISSING, None, []),
        (Presence.EMPTY, {}, []),
        (Presence.VALUE, {"entries": [{"id": 7}]}, [{"id": 7}]),
    ],
)
def test_workspace_list_success_preserves_structured_presence(
    monkeypatch,
    presence,
    structured_content,
    expected_entries,
):
    result = MCPToolResultEnvelope(
        ToolStatus.SUCCESS,
        structured_content_presence=presence,
        structured_content=structured_content,
        is_error_presence=Presence.VALUE,
        is_error=False,
    )

    response, hub = _run_list(monkeypatch, result)

    assert response.status_code == 200
    assert _body(response) == {
        "entries": expected_entries,
        "count": len(expected_entries),
    }
    assert hub.result is result
    assert hub.result.structured_content_presence is presence


@pytest.mark.parametrize(
    "result",
    [
        MCPToolResultEnvelope(
            ToolStatus.TOOL_FAILURE,
            structured_content_presence=Presence.VALUE,
            structured_content={"entries": [{"id": "must-not-succeed"}]},
            is_error_presence=Presence.VALUE,
            is_error=True,
        ),
        MCPToolResultEnvelope(
            ToolStatus.PROTOCOL_FAILURE,
            protocol_error={"code": -32603, "message": "looks successful"},
        ),
        MCPToolResultEnvelope(
            ToolStatus.TRANSPORT_FAILURE,
            transport_diagnostic="looks successful",
        ),
    ],
    ids=("tool-failure", "protocol-failure", "transport-failure"),
)
def test_workspace_list_failure_status_cannot_return_http_success(
    monkeypatch,
    result,
):
    response, hub = _run_list(monkeypatch, result)

    assert response.status_code >= 400
    assert hub.result is result


def test_workspace_get_success_ignores_error_shaped_display_payload(monkeypatch):
    workspace_routes = _load_workspace_routes()
    result = MCPToolResultEnvelope(
        ToolStatus.SUCCESS,
        structured_content_presence=Presence.VALUE,
        structured_content={"error": "display only", "entry_id": 7},
        is_error_presence=Presence.VALUE,
        is_error=False,
    )
    hub = _Hub(result)
    monkeypatch.setattr("mcp.hub.get_hub", lambda: hub)

    response = asyncio.run(workspace_routes.workspace_get(7))

    assert response.status_code == 200
    assert _body(response) == {"error": "display only", "entry_id": 7}
    assert hub.result is result
