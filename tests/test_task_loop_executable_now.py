from core.task_loop.contracts import StepExecutionStatus
from core.task_loop.executable_now import details_by_name
from core.task_loop.executor import TaskToolResult, execute_step
from core.thinking.contracts import PlanStep


def _step(arguments=None, tool="container_inspect"):
    return PlanStep(
        step_id="s1",
        title="Inspect",
        goal="Inspect container",
        tool=tool,
        tool_arguments=dict(arguments or {}),
    )


def test_missing_required_args_blocks_before_tool_runner():
    events = []
    called = {"value": False}

    def runner(_call):
        called["value"] = True
        return TaskToolResult(success=True, result={"ok": True})

    result = execute_step(
        _step(),
        runner,
        event_sink=lambda payload: events.append(dict(payload)),
        tool_details_by_name={
            "container_inspect": {
                "name": "container_inspect",
                "capability_required_args": ["container_id_or_name"],
            }
        },
    )

    assert called["value"] is False
    assert result.status == StepExecutionStatus.FAILED
    assert result.error == "missing_required_args:container_id_or_name"
    assert [event["type"] for event in events] == ["tool_result"]
    assert "error" not in events[0]


def test_bound_required_args_allow_tool_runner():
    seen = {}

    def runner(call):
        seen["arguments"] = dict(call.arguments)
        return TaskToolResult(success=True, result={"ok": True})

    result = execute_step(
        _step({"container_id_or_name": "trion-home"}),
        runner,
        tool_details_by_name={
            "container_inspect": {
                "name": "container_inspect",
                "capability_required_args": ["container_id_or_name"],
            }
        },
    )

    assert result.status == StepExecutionStatus.SUCCESS
    assert seen["arguments"] == {"container_id_or_name": "trion-home"}


def test_container_id_satisfies_container_id_or_name_contract():
    seen = {}

    def runner(call):
        seen["arguments"] = dict(call.arguments)
        return TaskToolResult(success=True, result={"ok": True})

    result = execute_step(
        _step({"container_id": "abc-123"}),
        runner,
        tool_details_by_name={
            "container_inspect": {
                "name": "container_inspect",
                "capability_required_args": ["container_id_or_name"],
            }
        },
    )

    assert result.status == StepExecutionStatus.SUCCESS
    assert seen["arguments"] == {"container_id": "abc-123"}


def test_tool_without_required_args_keeps_existing_execution():
    called = {"value": False}

    def runner(_call):
        called["value"] = True
        return TaskToolResult(success=True, result={"ok": True})

    result = execute_step(
        _step(tool="time_now"),
        runner,
        tool_details_by_name={"time_now": {"name": "time_now", "capability_required_args": []}},
    )

    assert called["value"] is True
    assert result.status == StepExecutionStatus.SUCCESS


def test_missing_tool_metadata_fails_closed_when_guard_is_active():
    called = {"value": False}

    def runner(_call):
        called["value"] = True
        return TaskToolResult(success=True, result={"ok": True})

    result = execute_step(_step(), runner, tool_details_by_name={})

    assert called["value"] is False
    assert result.status == StepExecutionStatus.FAILED
    assert result.error == "missing_tool_metadata"


def test_details_by_name_reads_registry_mirror_requires():
    details = details_by_name([
        {"name": "container_inspect", "tool_intent": {"requires": ["container_id_or_name"]}}
    ])

    assert details["container_inspect"]["capability_required_args"] == ["container_id_or_name"]
