import pytest

from core.orchestrator.contracts import OrchestratorPackage, ToolDescriptor
from core.pipeline.orchestrator_stage import build_orchestrator_stage
from tests._orchestrator_classifier_helpers import make_classifier_result


@pytest.mark.parametrize("detail_key", ["available_tool_details", "selected_tool_details"])
def test_tool_details_include_capability_target_scopes(detail_key):
    tool = ToolDescriptor(
        name="container_inspect",
        source="container-commander",
        capability_target_scopes=["runtime_state"],
    )

    def _orchestrator(*_args, **_kwargs):
        return OrchestratorPackage(
            available_tools=[tool],
            selected_tools=[tool],
            context={},
            classifier_result=make_classifier_result(needs_orchestrator=True),
        )

    stage = build_orchestrator_stage(
        "Inspect container",
        make_classifier_result(needs_orchestrator=True),
        conversation_id=f"conv-target-{detail_key}",
        orchestrator_fn=_orchestrator,
        raw_tools=[{"name": "container_inspect"}],
    )

    details = stage.thinking_context[detail_key]
    assert details[0]["capability_target_scopes"] == ["runtime_state"]
