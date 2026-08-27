from core.task_loop.contracts import StepExecutionStatus
from core.task_loop.executor import (
    TaskToolResult,
    TaskToolResultStatus,
    build_tool_call,
    execute_step,
)
from core.thinking.contracts import PlanStep


def _step(**updates) -> PlanStep:
    data = {
        "step_id": "step-1",
        "title": "Deploy",
        "goal": "Run tool",
        "tool": "deploy_container",
        "tool_arguments": {"blueprint": "python"},
    }
    data.update(updates)
    return PlanStep(**data)


def test_build_tool_call_uses_step_timeout():
    call = build_tool_call(_step(timeout_s=180.0), default_timeout_s=30.0)

    assert call.tool_name == "deploy_container"
    assert call.arguments == {"blueprint": "python"}
    assert call.step_id == "step-1"
    assert call.timeout_s == 180.0


def test_build_tool_call_falls_back_to_default_timeout():
    call = build_tool_call(_step(timeout_s=None), default_timeout_s=45.0)

    assert call.timeout_s == 45.0


def test_task_tool_result_distinguishes_success_presence():
    missing = TaskToolResult(status=TaskToolResultStatus.SUCCESS_MISSING)
    empty = TaskToolResult(status=TaskToolResultStatus.SUCCESS_EMPTY, result={})
    value = TaskToolResult(status=TaskToolResultStatus.SUCCESS_VALUE, result={"ok": True})

    assert (missing.status, empty.status, value.status) == (
        TaskToolResultStatus.SUCCESS_MISSING,
        TaskToolResultStatus.SUCCESS_EMPTY,
        TaskToolResultStatus.SUCCESS_VALUE,
    )
    assert missing.result == {}
    assert empty.result == {}
    assert value.result == {"ok": True}


def test_task_tool_result_success_is_derived_from_status():
    success = TaskToolResult(status=TaskToolResultStatus.SUCCESS_MISSING)
    failure = TaskToolResult(status=TaskToolResultStatus.PROTOCOL_FAILURE, error="bad response")

    assert success.success is True
    assert failure.success is False


def test_task_tool_result_legacy_success_projection_is_write_only():
    missing = TaskToolResult(success=True)
    empty = TaskToolResult(success=True, result={})
    value = TaskToolResult(success=True, result={"ok": True})
    failure = TaskToolResult(success=False, error="legacy failure")

    assert missing.status is TaskToolResultStatus.SUCCESS_MISSING
    assert empty.status is TaskToolResultStatus.SUCCESS_EMPTY
    assert value.status is TaskToolResultStatus.SUCCESS_VALUE
    assert failure.status is TaskToolResultStatus.TOOL_FAILURE


def test_execute_step_returns_success_and_artifacts():
    def runner(call):
        assert call.timeout_s == 180.0
        return TaskToolResult(success=True, result={"ok": True, "artifacts": [{"id": "a1"}]})

    result = execute_step(_step(timeout_s=180.0), runner)

    assert result.status == StepExecutionStatus.SUCCESS
    assert result.output == {"ok": True, "artifacts": [{"id": "a1"}]}
    assert {"id": "a1"} in result.artifacts  # collect_result_artifacts ergänzt synthetic artifact
    assert result.error is None


def test_execute_step_emits_tool_start_and_result_events():
    events = []

    def runner(call):
        return TaskToolResult(success=True, result={"ok": True, "artifacts": [{"id": "a1"}]})

    result = execute_step(_step(timeout_s=60.0), runner, event_sink=lambda payload: events.append(dict(payload)))

    assert result.status == StepExecutionStatus.SUCCESS
    # T12: Reihenfolge tool_start → progress_utterance → tool_result → progress_utterance
    assert [event["type"] for event in events] == [
        "tool_start", "progress_utterance", "tool_result", "progress_utterance"
    ]
    tool_start_ev = next(e for e in events if e["type"] == "tool_start")
    tool_result_ev = next(e for e in events if e["type"] == "tool_result")
    assert "tool_name" not in tool_start_ev
    assert "step_id" not in tool_start_ev
    assert tool_result_ev["status"] == "success"
    assert tool_result_ev["artifact_count"] >= 1  # original + synthetic tool_result artifact


def test_execute_step_skips_missing_tool_without_runner_call():
    def runner(call):
        raise AssertionError("runner must not be called")

    result = execute_step(_step(tool=None), runner)

    assert result.status == StepExecutionStatus.SKIPPED
    assert result.error == "missing_tool"


def test_execute_step_emits_skipped_tool_result_for_missing_tool():
    events = []

    result = execute_step(_step(tool=None), lambda call: None, event_sink=lambda payload: events.append(dict(payload)))

    assert result.status == StepExecutionStatus.SKIPPED
    assert events == [{
        "type": "tool_result", "status": "skipped", "success": False,
        "artifact_count": 0,
    }]


def test_execute_step_maps_tool_failure():
    def runner(call):
        return TaskToolResult(success=False, result={"details": "bad"}, error="tool_failed")

    result = execute_step(_step(), runner)

    assert result.status == StepExecutionStatus.FAILED
    assert result.output == {"details": "bad"}
    assert result.error == "tool_failed"


def test_execute_step_maps_mcp_timeout_error():
    def runner(call):
        return TaskToolResult(
            status=TaskToolResultStatus.TRANSPORT_FAILURE,
            error="mcp_timeout:deploy_container:30s",
        )

    result = execute_step(_step(), runner)

    assert result.status == StepExecutionStatus.TIMEOUT
    assert result.error == "mcp_timeout:deploy_container:30s"


def test_execute_step_sets_artifact_type_on_tool_result_artifact():
    """P2 / E3 Regression (Doc 51): executor produziert artifact_type='tool_result'
    in den gesammelten Artifacts, damit EvidenceArtifact.from_dict() korrekt konvertiert.
    """
    def runner(call):
        return TaskToolResult(success=True, result={"ok": True, "artifacts": [{"id": "a1"}]})

    result = execute_step(_step(timeout_s=30.0), runner)

    assert result.status == StepExecutionStatus.SUCCESS
    tool_result_artifacts = [a for a in result.artifacts if a.get("artifact_type") == "tool_result"]
    assert len(tool_result_artifacts) == 1, "mindestens ein artifact_type='tool_result' erwartet"
    assert tool_result_artifacts[0]["source_step_id"] == "step-1"


def test_execute_step_catches_runner_exception():
    def runner(call):
        raise RuntimeError("transport exploded")

    result = execute_step(_step(), runner)

    assert result.status == StepExecutionStatus.FAILED
    assert result.error == "transport exploded"
