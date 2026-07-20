from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tools import select_relevant_tools
from core.routing_frame.builder import build_routing_frame


def _classifier() -> ClassifierResult:
    return ClassifierResult(
        category=Category.INFORMATION,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=True,
        confidence=0.9,
        route=Route.NEEDS_ORCHESTRATOR,
        matched_pattern="test",
        reason="test",
    )


def _frame(text: str) -> dict:
    return build_routing_frame(text, _classifier())


def test_select_relevant_tools_fails_closed_without_routing_frame():
    selected = select_relevant_tools(
        "Pruefe den Container trion-home.",
        _classifier(),
        [
            ToolDescriptor(
                name="container_inspect",
                capability_domain="container_runtime",
                capability_operation="inspect",
                capability_evidence_types=["runtime_metadata", "home_scope"],
                capability_required_args=["container_id_or_name"],
                capability_risk="read_only",
            )
        ],
    )

    assert selected == []


def test_select_relevant_tools_fails_closed_without_operation_contract_key():
    selected = select_relevant_tools(
        "Suche 3x in deinen Erinnerungen nach verschiedenen Stichwoertern.",
        _classifier(),
        [
            ToolDescriptor(
                name="memory_graph_search",
                capability_domain="memory",
                capability_operation="graph_search",
                capability_target_scopes=["assistant_identity"],
                capability_risk="read_only",
            )
        ],
        routing_frame={
            "domain": "memory",
            "intent_kind": "task_loop_request",
            "execution_mode": "loop",
        },
    )

    assert selected == []


def test_select_relevant_tools_keeps_runtime_selection_with_operation_contract():
    text = "Laeuft der Container trion-home?"
    selected = select_relevant_tools(
        text,
        _classifier(),
        [
            ToolDescriptor(
                name="container_list",
                capability_domain="container_runtime",
                capability_operation="list",
                capability_entity_types=["container"],
                capability_evidence_types=["runtime_status"],
                capability_target_scopes=["runtime_state"],
                capability_risk="read_only",
            )
        ],
        routing_frame=_frame(text),
    )

    assert [tool.name for tool in selected] == ["container_list"]


def test_select_relevant_tools_keeps_memory_selection_with_operation_contract(monkeypatch):
    monkeypatch.setattr(
        "core.orchestrator.tools.select_top_k_tools",
        lambda user_text, tools, **kwargs: [tool for tool in tools if tool.name == "memory_graph_search"],
    )
    text = "Suche 3x in deinen Erinnerungen nach verschiedenen Stichwoertern."
    selected = select_relevant_tools(
        text,
        _classifier(),
        [
            ToolDescriptor(
                name="maintenance_run",
                capability_domain="memory",
                capability_operation="maintenance",
                capability_target_scopes=["assistant_identity"],
                capability_risk="mutating",
            ),
            ToolDescriptor(
                name="memory_graph_search",
                capability_domain="memory",
                capability_operation="graph_search",
                capability_evidence_types=["memory_context"],
                capability_target_scopes=["assistant_identity"],
                capability_risk="read_only",
            ),
        ],
        routing_frame=_frame(text),
    )

    assert [tool.name for tool in selected] == ["memory_graph_search"]


def test_select_relevant_tools_allows_time_tool_with_operation_contract():
    text = "Wie viel Uhr ist es gerade?"
    selected = select_relevant_tools(
        text,
        _classifier(),
        [
            ToolDescriptor(
                name="time_now",
                capability_domain="time",
                capability_operation="read",
                capability_evidence_types=["live_runtime"],
                capability_target_scopes=["time_reference"],
                capability_risk="read_only",
            )
        ],
        routing_frame=_frame(text),
    )

    assert [tool.name for tool in selected] == ["time_now"]
