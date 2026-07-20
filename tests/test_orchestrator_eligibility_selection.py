from core.classifier.contracts import Category
from core.orchestrator.orchestrator import orchestrate
from core.routing_frame.builder import build_routing_frame

from tests._eligible_tool_fixtures import eligible_raw_tool
from tests._orchestrator_classifier_helpers import make_classifier_result


def test_orchestrator_selects_relevant_tools_from_capability_rules(monkeypatch):
    monkeypatch.setattr(
        "core.orchestrator.tools.select_top_k_tools",
        lambda user_text, tools, **kwargs: [tool for tool in tools if tool.name == "request_container"],
    )

    text = "Starte einen Container und fuehre ein Bash Script aus"
    classifier = make_classifier_result()
    package = orchestrate(
        text,
        classifier,
        raw_tools=[
            eligible_raw_tool(
                "request_container",
                "Container deployment",
                "container-commander",
                {
                    "domain": "container_runtime",
                    "operation": "start",
                    "supports_entities": ["container"],
                    "evidence_types": ["runtime_state_change"],
                    "target_scopes": ["runtime_state"],
                    "risk": "mutating",
                },
            ),
            eligible_raw_tool("memory_save", "Persist a memory entry", "sql-memory"),
        ],
        conversation_id="conv-1",
        routing_frame=build_routing_frame(text, classifier),
    )

    assert [tool.name for tool in package.available_tools] == ["request_container", "memory_save"]
    assert [tool.name for tool in package.selected_tools] == ["request_container"]
    assert package.context["conversation_id"] == "conv-1"
    assert package.context["conversation_meta"]["conversation_id"] == "conv-1"
    assert package.classifier_result.needs_orchestrator is True


def test_orchestrator_direct_path_keeps_tools_available_but_selects_none():
    package = orchestrate(
        "Hallo",
        make_classifier_result(needs_orchestrator=False, category=Category.INFORMATION),
        raw_tools=[eligible_raw_tool("memory_save", "Memory", "sql-memory")],
    )

    assert [tool.name for tool in package.available_tools] == ["memory_save"]
    assert package.selected_tools == []
    assert package.context["conversation_id"] == "global"
    assert package.context["conversation_meta_source"] == "default"


def test_orchestrator_prefers_tool_intents_for_time_queries(monkeypatch):
    monkeypatch.setattr(
        "core.orchestrator.tools.select_top_k_tools",
        lambda user_text, tools, **kwargs: [tool for tool in tools if tool.name == "time_now"],
    )

    text = "Wie viel Uhr ist es gerade?"
    classifier = make_classifier_result()
    package = orchestrate(
        text,
        classifier,
        raw_tools=[
            eligible_raw_tool(
                "time_now",
                "Return current UTC time and date.",
                "time-mcp",
                {
                    "domain": "time",
                    "operation": "read",
                    "evidence_types": ["live_runtime"],
                    "target_scopes": ["time_reference"],
                    "risk": "read_only",
                },
            ),
            eligible_raw_tool("memory_save", "Persist a memory entry", "sql-memory"),
        ],
        routing_frame=build_routing_frame(text, classifier),
    )

    assert [tool.name for tool in package.selected_tools] == ["time_now"]


def test_orchestrator_does_not_fallback_to_all_tools_when_selector_rejects(monkeypatch):
    monkeypatch.setattr("core.orchestrator.tools.select_top_k_tools", lambda *args, **kwargs: [])

    package = orchestrate(
        "Lies die Datei /trion-home/status.txt",
        make_classifier_result(),
        raw_tools=[
            {
                "name": "container_list",
                "description": "List running containers",
                "mcp": "container-commander",
            },
            {
                "name": "time_now",
                "description": "Return current UTC time and date.",
                "mcp": "time-mcp",
            },
        ],
    )

    assert package.selected_tools == []


def test_orchestrator_does_not_route_container_capability_question_to_inventory(monkeypatch):
    monkeypatch.setattr(
        "core.orchestrator.tools.select_top_k_tools",
        lambda user_text, tools, **kwargs: [tool for tool in tools if tool.name == "container_list"],
    )

    text = "Was kannst du in diesem Container alles machen?"
    classifier = make_classifier_result(needs_orchestrator=True, category=Category.INFORMATION)
    package = orchestrate(
        text,
        classifier,
        raw_tools=[
            eligible_raw_tool(
                "container_list",
                "List running containers",
                "container-commander",
                {"domain": "container_runtime", "operation": "list", "evidence_types": ["runtime_inventory"], "risk": "read_only"},
            ),
            eligible_raw_tool(
                "container_inspect",
                "Inspect container metadata",
                "container-commander",
                {
                    "domain": "container_runtime",
                    "operation": "inspect",
                    "evidence_types": ["runtime_metadata", "home_scope"],
                    "requires": ["container_id_or_name"],
                    "risk": "read_only",
                },
            ),
        ],
        routing_frame=build_routing_frame(text, classifier),
    )

    assert package.selected_tools == []


def test_orchestrator_live_claim_information_queries_bypass_family_filter(monkeypatch):
    monkeypatch.setattr(
        "core.orchestrator.tools.select_top_k_tools",
        lambda user_text, tools, **kwargs: [tool for tool in tools if tool.name == "time_now"],
    )

    text = "Wie viel Uhr ist es gerade?"
    classifier = make_classifier_result(needs_orchestrator=True, category=Category.INFORMATION)
    package = orchestrate(
        text,
        classifier,
        raw_tools=[
            eligible_raw_tool(
                "time_now",
                "Return current UTC time and date.",
                "time-mcp",
                {
                    "domain": "time",
                    "operation": "read",
                    "evidence_types": ["live_runtime"],
                    "target_scopes": ["time_reference"],
                    "risk": "read_only",
                },
            ),
            eligible_raw_tool("container_list", "List running containers", "container-commander"),
        ],
        routing_frame=build_routing_frame(text, classifier),
    )

    assert [tool.name for tool in package.selected_tools] == ["time_now"]
