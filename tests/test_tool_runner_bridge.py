import json

from adapters import tool_runner_bridge
from adapters.tool_runner_bridge import _tool_intent_for, make_tool_runner, project_task_tool_result
from core.task_loop.executor import TaskToolCall, TaskToolResultStatus
from mcp.tool_result_contracts import (
    MCPResultPresence as Presence,
    MCPToolCallStatus as ToolStatus,
    MCPToolResultEnvelope,
)
from tools.contracts import ToolResult


def test_project_task_tool_result_preserves_success_presence():
    cases = (
        (MCPToolResultEnvelope(ToolStatus.SUCCESS), TaskToolResultStatus.SUCCESS_MISSING),
        (
            MCPToolResultEnvelope(
                ToolStatus.SUCCESS,
                structured_content_presence=Presence.EMPTY,
                structured_content={},
            ),
            TaskToolResultStatus.SUCCESS_EMPTY,
        ),
        (
            MCPToolResultEnvelope(
                ToolStatus.SUCCESS,
                structured_content_presence=Presence.VALUE,
                structured_content={"value": 1},
            ),
            TaskToolResultStatus.SUCCESS_VALUE,
        ),
    )

    for envelope, expected_status in cases:
        projected = project_task_tool_result(envelope)
        assert projected.status is expected_status
        assert projected.success is True


def test_project_task_tool_result_preserves_failure_class():
    envelopes = (
        MCPToolResultEnvelope(
            ToolStatus.TOOL_FAILURE,
            is_error_presence=Presence.VALUE,
            is_error=True,
        ),
        MCPToolResultEnvelope(ToolStatus.PROTOCOL_FAILURE),
        MCPToolResultEnvelope(
            ToolStatus.TRANSPORT_FAILURE,
            transport_diagnostic="offline",
        ),
    )
    expected = (TaskToolResultStatus.TOOL_FAILURE, TaskToolResultStatus.PROTOCOL_FAILURE,
                TaskToolResultStatus.TRANSPORT_FAILURE)

    assert tuple(project_task_tool_result(item).status for item in envelopes) == expected


def test_make_tool_runner_uses_imported_run_tool_binding(monkeypatch):
    envelope = MCPToolResultEnvelope(
        ToolStatus.SUCCESS,
        structured_content_presence=Presence.VALUE,
        structured_content={"ok": True},
    )
    seen = []

    def fake_run_tool(tool_call):
        seen.append(tool_call)
        return ToolResult(tool_call.tool_name, tool_call.step_id, envelope, 0.25)

    monkeypatch.setattr(tool_runner_bridge, "run_tool", fake_run_tool)
    result = make_tool_runner()(TaskToolCall("demo", {"x": 1}, "step-1", 2.0))

    assert result.status is TaskToolResultStatus.SUCCESS_VALUE
    assert result.result == {"structuredContent": {"ok": True}}
    assert seen[0].tool_name == "demo"


def test_project_task_tool_result_rejects_noncanonical_input():
    try:
        project_task_tool_result({"result": {}})
    except TypeError as exc:
        assert str(exc) == "envelope must be MCPToolResultEnvelope"
    else:
        raise AssertionError("non-canonical input must fail closed")


def test_tool_intent_for_prefers_registry_tool_intents_when_present(tmp_path):
    bundle = tmp_path / "time-mcp"
    bundle.mkdir()
    (bundle / "tool_intents.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tools": [{"name": "time_now", "description": "Bundle intent"}],
            }
        ),
        encoding="utf-8",
    )

    intent = _tool_intent_for(
        "time_now",
        {
            "cwd": str(bundle),
            "tool_intents": {
                "schema_version": 1,
                "tools": [{"name": "time_now", "description": "Registry intent"}],
            },
        },
    )

    assert intent["description"] == "Registry intent"


def test_tool_intent_for_returns_empty_when_no_registry_mirror_present(tmp_path):
    """P11.0-Zielvertrag: kein Bundle-Fallback im Request-Pfad. Fehlt der
    Registry-Mirror (config ohne 'tool_intents'), liefert _tool_intent_for()
    kein Intent zurueck - auch wenn das Bundle selbst ein vollstaendiges,
    gueltiges tool_intents.json mit Capability-Feldern enthaelt.
    """
    bundle = tmp_path / "container-commander"
    bundle.mkdir()
    (bundle / "tool_intents.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tools": [
                    {
                        "name": "container_inspect",
                        "description": "Inspect a container",
                        "domain": "container_runtime",
                        "operation": "inspect",
                        "supports_entities": ["container"],
                        "evidence_types": ["runtime_metadata", "home_scope"],
                        "requires": ["container_id_or_name"],
                        "risk": "read_only",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    intent = _tool_intent_for("container_inspect", {"cwd": str(bundle)})

    assert intent == {}


def test_tool_intent_for_returns_only_what_registry_mirror_declares():
    """Guarantee re-scoped from the removed bundle-fallback test to the
    registry/mirror path: _tool_intent_for() must not add fields beyond what
    the registry's tool_intents entry declares."""
    intent = _tool_intent_for(
        "container_inspect",
        {
            "tool_intents": {
                "schema_version": 1,
                "tools": [{"name": "container_inspect", "description": "Inspect a container"}],
            }
        },
    )

    assert intent["name"] == "container_inspect"
    assert intent["description"] == "Inspect a container"
    for forbidden in ("domain", "operation", "risk", "evidence_types", "requires"):
        assert forbidden not in intent


def test_tool_intent_for_passes_through_capability_fields_declared_in_registry_mirror():
    """Guarantee re-scoped from the removed bundle-fallback test to the
    registry/mirror path: capability fields declared in the registry's
    tool_intents entry must fully reach the runtime path."""
    intent = _tool_intent_for(
        "container_inspect",
        {
            "tool_intents": {
                "schema_version": 1,
                "tools": [
                    {
                        "name": "container_inspect",
                        "description": "Inspect a container",
                        "domain": "container_runtime",
                        "operation": "inspect",
                        "supports_entities": ["container"],
                        "evidence_types": ["runtime_metadata", "home_scope"],
                        "requires": ["container_id_or_name"],
                        "risk": "read_only",
                    }
                ],
            }
        },
    )

    assert intent["domain"] == "container_runtime"
    assert intent["operation"] == "inspect"
    assert intent["evidence_types"] == ["runtime_metadata", "home_scope"]
    assert intent["requires"] == ["container_id_or_name"]
    assert intent["risk"] == "read_only"
