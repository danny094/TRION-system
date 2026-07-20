from tools.contracts import ToolCall
from tools.executor import run_tool


def test_run_tool_returns_success_result_from_mcp_payload():
    seen = {}

    def fake_call_tool(name, arguments, timeout):
        seen["name"] = name
        seen["arguments"] = arguments
        seen["timeout"] = timeout
        return {"result": {"ok": True, "value": 42}}

    result = run_tool(
        ToolCall(
            tool_name="demo_tool",
            arguments={"x": 1},
            step_id="step-1",
            timeout_s=2.5,
        ),
        call_tool_fn=fake_call_tool,
    )

    assert result.success is True
    assert result.tool_name == "demo_tool"
    assert result.step_id == "step-1"
    assert result.result == {"ok": True, "value": 42}
    assert result.error is None
    assert result.duration_s >= 0
    assert seen == {"name": "demo_tool", "arguments": {"x": 1}, "timeout": 2.5}


def test_run_tool_returns_failure_for_mcp_error_payload():
    def fake_call_tool(name, arguments, timeout):
        return {"error": "tool_not_found"}

    result = run_tool(ToolCall(tool_name="missing", step_id="step-2"), fake_call_tool)

    assert result.success is False
    assert result.tool_name == "missing"
    assert result.step_id == "step-2"
    assert result.error == "tool_not_found"
    assert result.result == {"error": "tool_not_found"}


def test_run_tool_catches_call_tool_exceptions():
    def fake_call_tool(name, arguments, timeout):
        raise RuntimeError("transport failed")

    result = run_tool(ToolCall(tool_name="unstable", step_id="step-3"), fake_call_tool)

    assert result.success is False
    assert result.tool_name == "unstable"
    assert result.step_id == "step-3"
    assert result.error == "transport failed"
    assert result.result == {}


def test_run_tool_rejects_missing_tool_name_without_calling_mcp():
    def fail_call_tool(name, arguments, timeout):
        raise AssertionError("MCP must not be called without tool name")

    result = run_tool(ToolCall(tool_name="", step_id="step-4"), fail_call_tool)

    assert result.success is False
    assert result.tool_name == ""
    assert result.step_id == "step-4"
    assert result.error == "missing_tool_name"
    assert result.result == {}
