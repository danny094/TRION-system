from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.pipeline.routing_frame_stage import build_routing_frame_stage
from core.pipeline.thinking_stage import build_thinking_stage


def _classifier(*, needs_orchestrator: bool, category: Category, route: Route | None = None) -> ClassifierResult:
    return ClassifierResult(
        category=category,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=needs_orchestrator,
        confidence=0.9,
        route=route or (Route.NEEDS_ORCHESTRATOR if needs_orchestrator else Route.DIRECT_TO_THINKING),
        matched_pattern="test",
        reason="test",
    )


def test_routing_frame_stage_builds_shadow_frame_for_direct_request():
    result = build_routing_frame_stage(
        "Was kannst du gerade insgesamt im System tun?",
        _classifier(needs_orchestrator=False, category=Category.INFORMATION),
        orchestrator_thinking_context=None,
    )

    frame = result.context["routing_frame"]
    assert frame["intent_kind"] == "capability_question"
    assert frame["domain"] == "tools"
    assert frame["evidence_need"] == "self_context"
    assert frame["execution_mode"] == "direct_answer"
    assert frame["source_signals"]["classifier"]["route"] == "direct_to_thinking"


def test_routing_frame_stage_detects_loop_markers_and_container_scope():
    result = build_routing_frame_stage(
        "Pruefe den Container trion-home 5x und probiere das naechste wenn das nicht klappt.",
        _classifier(needs_orchestrator=True, category=Category.INFORMATION, route=Route.NEEDS_ORCHESTRATOR),
        orchestrator_thinking_context={
            "selected_tool_details": [
                {
                    "name": "container_inspect",
                    "capability_domain": "container_runtime",
                    "capability_operation": "inspect",
                }
            ],
            "context": {
                "home_context": {
                    "verified": True,
                    "container_name": "trion-home",
                }
            },
        },
    )

    frame = result.context["routing_frame"]
    assert frame["intent_kind"] == "task_loop_request"
    assert frame["domain"] == "container_runtime"
    assert frame["execution_mode"] == "loop"
    assert frame["evidence_need"] == "live_runtime"
    assert frame["source_signals"]["repeat_count"] == 5
    assert frame["source_signals"]["home_scope_verified"] is True


def test_thinking_stage_merges_routing_frame_into_context():
    stage = build_thinking_stage(
        "Hallo",
        _classifier(needs_orchestrator=False, category=Category.INFORMATION),
        build_plan_fn=lambda *_args, **_kwargs: "plan",
        orchestrator_thinking_context=None,
        routing_frame_thinking_context={"context": {"routing_frame": {"intent_kind": "conceptual_question"}}},
        document_tools_thinking_context=None,
        document_context=None,
    )

    assert stage.plan == "plan"
    assert stage.thinking_context["context"]["routing_frame"]["intent_kind"] == "conceptual_question"
