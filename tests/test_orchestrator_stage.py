"""P11.0 SP4 Round 3: Datei wuchs durch SP4 auf 384 Zeilen und wurde nach
Doc 07 (Max 200 Zeilen pro Datei) aufgeteilt. Hier bleibt: Basisrouting,
Skip-Pfad ohne Tools, Frame-basierte Loop-Aktivierung trotz direktem
Classifier-Routing, Routing-Frame-Weitergabe an den Orchestrator.
Ausgelagert: tests/test_orchestrator_stage_tool_metadata.py (Evidence-/
Tool-Metadaten), tests/test_orchestrator_stage_context.py (Home-/
Self-Context).
"""

from core.classifier.contracts import Category
from core.orchestrator.contracts import OrchestratorPackage, ToolDescriptor
from core.orchestrator.orchestrator import orchestrate
from core.pipeline.orchestrator_stage import build_orchestrator_stage

from tests._orchestrator_classifier_helpers import make_classifier_result


def test_orchestrator_stage_skips_direct_requests_without_tools():
    stage = build_orchestrator_stage(
        "Hallo",
        make_classifier_result(needs_orchestrator=False, category=Category.INFORMATION),
        conversation_id="conv-1",
        orchestrator_fn=orchestrate,
        raw_tools=[],
    )

    assert stage.context == {}
    assert stage.thinking_context is None


def test_orchestrator_stage_runs_for_frame_based_memory_loop_even_when_classifier_is_direct():
    seen = {}

    def _orchestrator(*args, **kwargs):
        seen["called"] = True
        return OrchestratorPackage(
            available_tools=[ToolDescriptor(name="memory_graph_search", source="memory-mcp")],
            selected_tools=[ToolDescriptor(name="memory_graph_search", source="memory-mcp")],
            context={},
            classifier_result=make_classifier_result(needs_orchestrator=False, category=Category.INFORMATION),
        )

    stage = build_orchestrator_stage(
        "Suche 3x in deinen Erinnerungen.",
        make_classifier_result(needs_orchestrator=False, category=Category.INFORMATION),
        conversation_id="conv-loop",
        orchestrator_fn=_orchestrator,
        raw_tools=[],
        routing_frame={
            "intent_kind": "task_loop_request",
            "domain": "memory",
            "evidence_need": "memory_context",
            "execution_mode": "loop",
        },
    )

    assert seen["called"] is True
    assert stage.thinking_context is not None
    assert stage.thinking_context["selected_tools"] == ["memory_graph_search"]


def test_orchestrator_stage_forwards_routing_frame_to_orchestrator():
    seen = {}

    def _orchestrator(*args, **kwargs):
        seen["routing_frame"] = kwargs.get("routing_frame")
        return OrchestratorPackage(
            available_tools=[],
            selected_tools=[],
            context={},
            classifier_result=make_classifier_result(needs_orchestrator=False, category=Category.INFORMATION),
        )

    stage = build_orchestrator_stage(
        "Suche in Erinnerungen",
        make_classifier_result(needs_orchestrator=False, category=Category.INFORMATION),
        conversation_id="conv-routing",
        orchestrator_fn=_orchestrator,
        raw_tools=[{"name": "memory_graph_search"}],
        routing_frame={"domain": "memory", "intent_kind": "capability_test", "execution_mode": "loop"},
    )

    assert seen["routing_frame"]["domain"] == "memory"
    assert stage.thinking_context is not None
    assert stage.thinking_context["context"]["routing_frame"]["domain"] == "memory"
