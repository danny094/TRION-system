from core.orchestrator.contracts import ToolDescriptor
from core.task_loop.executable_now import details_by_name
from core.task_loop.executor import TaskToolResult, execute_step
from core.thinking.contracts import PlanStep


def _step() -> PlanStep:
    return PlanStep(
        step_id="s1",
        title="Inspect",
        goal="Inspect runtime",
        tool="inspect_container",
    )


def test_details_by_name_preserves_descriptor_output_schema():
    details = details_by_name(
        [
            ToolDescriptor(
                name="inspect_container",
                capability_evidence_types=["runtime_status"],
                capability_output_schema="mcp_output_schema",
            )
        ]
    )

    assert details["inspect_container"]["capability_output_schema"] == "mcp_output_schema"


def test_details_by_name_defaults_descriptor_output_schema_to_empty_string():
    details = details_by_name([ToolDescriptor(name="inspect_container")])

    assert details["inspect_container"]["capability_output_schema"] == ""


def test_executor_passes_output_schema_detail_to_evidence_adapter(monkeypatch):
    seen = {}

    def fake_evidence_adapter(**kwargs):
        seen["tool_detail"] = kwargs["tool_detail"]
        return []

    monkeypatch.setattr(
        "core.task_loop.executor.validated_evidence_artifacts",
        fake_evidence_adapter,
    )

    result = execute_step(
        _step(),
        lambda _call: TaskToolResult(success=True, result={"status": "running"}),
        tool_details_by_name=details_by_name(
            [
                ToolDescriptor(
                    name="inspect_container",
                    capability_evidence_types=["runtime_status"],
                    capability_output_schema="mcp_output_schema",
                )
            ]
        ),
    )

    assert result.error is None
    assert seen["tool_detail"]["capability_output_schema"] == "mcp_output_schema"
    assert [item["artifact_type"] for item in result.artifacts] == ["tool_result"]
