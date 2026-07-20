from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_candidates.service import select_top_k_tools


def test_select_top_k_tools_prefers_semantic_signal(monkeypatch):
    tools = [
        ToolDescriptor(
            name="time_now",
            description="Return current UTC time and date.",
            intent_description="Return the current UTC time and date for TRION.",
            intent_examples=["Wie viel Uhr ist es?"],
            intent_keywords=["uhrzeit", "zeit", "datum"],
        ),
        ToolDescriptor(
            name="memory_save",
            description="Persist a memory entry",
            intent_description="Store a memory for later use.",
        ),
    ]

    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.semantic_score",
        lambda user_text, tool: 0.9 if tool.name == "time_now" else 0.0,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.score_tool_breakdown",
        lambda user_text, tool: type(
            "Score",
            (),
            {"total": 0, "keyword_hits": 0},
        )(),
    )

    selected = select_top_k_tools("Wie viel Uhr ist es gerade?", tools, top_k=1)

    assert [tool.name for tool in selected] == ["time_now"]


def test_select_top_k_tools_rejects_candidates_below_similarity_floor(monkeypatch):
    tools = [
        ToolDescriptor(name="container_list", description="List running containers."),
        ToolDescriptor(name="time_now", description="Return current UTC time and date."),
    ]

    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.semantic_score",
        lambda user_text, tool: 0.40 if tool.name == "container_list" else 0.20,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.score_tool_breakdown",
        lambda user_text, tool: type(
            "Score",
            (),
            {"total": 8, "keyword_hits": 0},
        )(),
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_min_similarity",
        lambda: 0.55,
    )

    selected = select_top_k_tools("Lies /trion-home/status.txt", tools, top_k=2)

    assert selected == []


def test_select_top_k_tools_requires_lexical_support_in_middle_zone(monkeypatch):
    tools = [
        ToolDescriptor(name="status_read", description="Read a status file."),
        ToolDescriptor(name="container_list", description="List running containers."),
    ]

    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.semantic_score",
        lambda user_text, tool: 0.70 if tool.name == "status_read" else 0.30,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.score_tool_breakdown",
        lambda user_text, tool: type(
            "Score",
            (),
            {"total": 0, "keyword_hits": 0},
        )(),
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_min_similarity",
        lambda: 0.55,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_high_similarity",
        lambda: 0.80,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_lexical_support_min",
        lambda: 2,
    )

    selected = select_top_k_tools("Lies /trion-home/status.txt", tools, top_k=1)

    assert selected == []


def test_select_top_k_tools_accepts_middle_zone_with_lexical_support(monkeypatch):
    tools = [
        ToolDescriptor(name="status_read", description="Read a status file."),
        ToolDescriptor(name="container_list", description="List running containers."),
    ]

    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.semantic_score",
        lambda user_text, tool: 0.70 if tool.name == "status_read" else 0.30,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.score_tool_breakdown",
        lambda user_text, tool: type(
            "Score",
            (),
            {"total": 3 if tool.name == "status_read" else 0, "keyword_hits": 0},
        )(),
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_min_similarity",
        lambda: 0.55,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_high_similarity",
        lambda: 0.80,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_lexical_support_min",
        lambda: 2,
    )

    selected = select_top_k_tools("Lies /trion-home/status.txt", tools, top_k=1)

    assert [tool.name for tool in selected] == ["status_read"]


def test_select_top_k_tools_rejects_ambiguous_mid_confidence_candidates(monkeypatch):
    tools = [
        ToolDescriptor(name="container_list", description="List running containers."),
        ToolDescriptor(name="container_logs", description="Read container logs."),
    ]

    semantic_scores = {"container_list": 0.70, "container_logs": 0.69}
    lexical_scores = {"container_list": 3, "container_logs": 3}

    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.semantic_score",
        lambda user_text, tool: semantic_scores[tool.name],
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.score_tool_breakdown",
        lambda user_text, tool: type(
            "Score",
            (),
            {"total": lexical_scores[tool.name], "keyword_hits": 0, "example_hits": 0},
        )(),
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_min_similarity",
        lambda: 0.55,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_high_similarity",
        lambda: 0.80,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_lexical_support_min",
        lambda: 2,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_ambiguity_margin",
        lambda: 0.08,
    )

    selected = select_top_k_tools("Lies eine Datei aus dem Container", tools, top_k=1)

    assert selected == []


def test_select_top_k_tools_can_degrade_to_lexical_only_for_clear_time_query(monkeypatch):
    tools = [
        ToolDescriptor(name="time_now", description="Return current UTC time and date."),
        ToolDescriptor(name="container_list", description="List running containers."),
    ]

    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.semantic_score",
        lambda user_text, tool: None,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.score_tool_breakdown",
        lambda user_text, tool: type(
            "Score",
            (),
            {
                "total": 8 if tool.name == "time_now" else 0,
                "keyword_hits": 1 if tool.name == "time_now" else 0,
                "example_hits": 1 if tool.name == "time_now" else 0,
            },
        )(),
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_lexical_only_min",
        lambda: 6,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_lexical_only_keyword_hits_min",
        lambda: 2,
    )

    selected = select_top_k_tools("Wie spät ist es gerade?", tools, top_k=1)

    assert [tool.name for tool in selected] == ["time_now"]


def test_select_top_k_tools_rejects_lexical_only_without_keyword_support(monkeypatch):
    tools = [
        ToolDescriptor(name="time_now", description="Return current UTC time and date."),
        ToolDescriptor(name="container_list", description="List running containers."),
    ]

    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.semantic_score",
        lambda user_text, tool: None,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.score_tool_breakdown",
        lambda user_text, tool: type(
            "Score",
            (),
            {
                "total": 8 if tool.name == "container_list" else 4,
                "keyword_hits": 1 if tool.name == "container_list" else 0,
                "example_hits": 0,
            },
        )(),
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_lexical_only_min",
        lambda: 6,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_lexical_only_keyword_hits_min",
        lambda: 2,
    )

    selected = select_top_k_tools("Lies die Datei /trion-home/status.txt", tools, top_k=1)

    assert selected == []


def test_select_top_k_tools_lexical_only_preserves_ranking_for_container_queries(monkeypatch):
    tools = [
        ToolDescriptor(name="container_list", description="List running containers."),
        ToolDescriptor(name="container_logs", description="Read container logs."),
    ]

    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.semantic_score",
        lambda user_text, tool: None,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.score_tool_breakdown",
        lambda user_text, tool: type(
            "Score",
            (),
            {
                "total": 28 if tool.name == "container_list" else 12,
                "keyword_hits": 4 if tool.name == "container_list" else 2,
                "example_hits": 1 if tool.name == "container_list" else 0,
            },
        )(),
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_lexical_only_min",
        lambda: 6,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_lexical_only_keyword_hits_min",
        lambda: 2,
    )
    monkeypatch.setattr(
        "core.orchestrator.tool_candidates.service.get_tool_selector_ambiguity_margin",
        lambda: 0.08,
    )

    selected = select_top_k_tools("Welche Container laufen gerade?", tools, top_k=1)

    assert [tool.name for tool in selected] == ["container_list"]
