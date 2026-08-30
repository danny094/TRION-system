"""Tool- und Evidence-Metadaten in orchestrator_stage.

Zwei Themen in einer Datei, bewusst per Danny-Entscheidung (SP4 Round 3,
2026-06-22) statt eigener Datei: (1) tool_role/capability_risk in
available_tool_details/selected_tool_details (P10.1-Regression - ohne diese
Felder kann prompts._tools_json() sie im realen Pipeline-Pfad nicht
injizieren), (2) Tool-Kandidaten aus raw_tools/tool_intent und
capability_evidence_types in denselben Detail-Listen (SP4-Split aus
tests/test_orchestrator_stage.py, Doc 07 Max 200 Zeilen pro Datei).
Basisrouting bleibt in tests/test_orchestrator_stage.py, Home-/Self-Context
in tests/test_orchestrator_stage_context.py.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from core.classifier.contracts import Category
from core.orchestrator.contracts import OrchestratorPackage, ToolDescriptor
from core.orchestrator.orchestrator import orchestrate
from core.pipeline.orchestrator_stage import build_orchestrator_stage

from tests._orchestrator_classifier_helpers import make_classifier_result
from tests.operation_contract_context import canonical_contract_context

_VALID_TOOL_INTENT_META = {
    "schema_version": 1,
    "source_sha256": "a" * 64,
    "bundle_version": "1.0.0-test",
}


def _tool(name: str, tool_role: str = "primary", capability_risk: str = "read") -> ToolDescriptor:
    return ToolDescriptor(
        name=name,
        description="",
        source="memory-mcp",
        capability_domain="memory",
        capability_operation="semantic_search",
        capability_entity_types=[],
        capability_evidence_types=[],
        capability_required_args=["query"],
        capability_risk=capability_risk,
        capability_target_scopes=[],
        tool_role=tool_role,
        intent_description="",
        intent_keywords=[],
    )


def _fake_orchestrator(tools: list[ToolDescriptor]):
    def _fn(user_text: Any, classifier_result: Any, **kwargs: Any) -> OrchestratorPackage:
        return OrchestratorPackage(
            available_tools=tools,
            selected_tools=tools[:1],
            context={},
            classifier_result=classifier_result,
        )
    return _fn


def test_available_tool_details_includes_tool_role_and_risk():
    tool = _tool("memory_search", tool_role="primary", capability_risk="read")
    result = build_orchestrator_stage(
        "Suche etwas.",
        MagicMock(needs_orchestrator=True),
        conversation_id="test",
        orchestrator_fn=_fake_orchestrator([tool]),
        raw_tools=[tool],
    )
    details = (result.thinking_context or {}).get("available_tool_details", [])
    assert len(details) == 1
    assert details[0]["tool_role"] == "primary"
    assert details[0]["capability_risk"] == "read"


def test_selected_tool_details_includes_tool_role_and_risk():
    tool = _tool("memory_search", tool_role="supporting", capability_risk="mutating")
    result = build_orchestrator_stage(
        "Suche etwas.",
        MagicMock(needs_orchestrator=True),
        conversation_id="test",
        orchestrator_fn=_fake_orchestrator([tool]),
        raw_tools=[tool],
    )
    details = (result.thinking_context or {}).get("selected_tool_details", [])
    assert len(details) == 1
    assert details[0]["tool_role"] == "supporting"
    assert details[0]["capability_risk"] == "mutating"


def test_orchestrator_stage_keeps_tool_candidates_for_direct_information_queries():
    def _orchestrator(*args, **kwargs):
        return OrchestratorPackage(
            available_tools=[ToolDescriptor(name="time_now", source="time-mcp")],
            selected_tools=[ToolDescriptor(name="time_now", source="time-mcp")],
            context={},
            classifier_result=make_classifier_result(needs_orchestrator=False, category=Category.INFORMATION),
        )

    stage = build_orchestrator_stage(
        "Wie viel Uhr ist es gerade?",
        make_classifier_result(needs_orchestrator=False, category=Category.INFORMATION),
        conversation_id="conv-2",
        orchestrator_fn=_orchestrator,
        raw_tools=[{
            "name": "time_now",
            "description": "Return current UTC time and date.",
            "mcp": "time-mcp",
            "tool_intent": {
                "name": "time_now",
                "description": "Return the current UTC time and date for TRION.",
                "examples": ["Wie viel Uhr ist es?"],
                "keywords": ["uhrzeit", "zeit", "datum", "utc", "time", "clock"],
                "tool_intent_meta": _VALID_TOOL_INTENT_META,
            },
        }],
    )

    assert stage.thinking_context is not None
    assert stage.thinking_context["selected_tools"] == ["time_now"]
    assert stage.thinking_context["available_tools"] == ["time_now"]


def test_orchestrator_stage_keeps_memory_search_candidate_for_direct_looped_memory_request():
    stage = build_orchestrator_stage(
        "Prüf mal über die Stichwortsuche in deinen Erinnerungen etwas und versuch es 5x.",
        make_classifier_result(needs_orchestrator=False, category=Category.INFORMATION),
        conversation_id="conv-memory",
        orchestrator_fn=orchestrate,
        raw_tools=[
            {
                "name": "memory_save", "description": "Persist a memory entry", "mcp": "sql-memory",
                "tool_intent": {
                    "name": "memory_save",
                    "domain": "memory", "operation": "save", "description": "Store a memory.",
                    "keywords": ["memory", "save"], "tool_intent_meta": _VALID_TOOL_INTENT_META,
                },
            },
            {
                "name": "memory_graph_search", "description": "Search graph memory", "mcp": "sql-memory",
                "tool_intent": {
                    "name": "memory_graph_search",
                    "domain": "memory", "operation": "graph_search",
                    "description": "Search memory relationships.",
                    "evidence_types": ["memory_context"],
                    "target_scopes": ["assistant_identity"],
                    "risk": "read_only",
                    "keywords": ["memory", "search", "graph", "recall"], "tool_intent_meta": _VALID_TOOL_INTENT_META,
                },
            },
        ],
        routing_frame={
            "domain": "memory", "intent_kind": "task_loop_request",
            "evidence_need": "memory_context", "execution_mode": "loop",
            "operation_contract": canonical_contract_context(
                domain="memory", primary_operation="search", target="",
                required_evidence=("memory_context",), allowed_operations=("search",), scope_lock="",
            )["routing_frame"]["operation_contract"],
        },
    )

    assert stage.thinking_context is not None
    assert stage.thinking_context["selected_tools"] == ["memory_graph_search"]


@pytest.mark.parametrize("detail_key", ["available_tool_details", "selected_tool_details"])
def test_build_orchestrator_stage_includes_capability_evidence_types_in_tool_details(detail_key):
    """T1/T2: capability_evidence_types landet sowohl in available_tool_details
    als auch in selected_tool_details (C1-Regression)."""
    _evidence_tool = ToolDescriptor(
        name="container_inspect",
        source="container-commander",
        capability_evidence_types=["thermal_scan"],
    )

    def _orchestrator(*args, **kwargs):
        return OrchestratorPackage(
            available_tools=[_evidence_tool],
            selected_tools=[_evidence_tool],  # mind. 1 → should_keep_orchestrator_context=True
            context={},
            classifier_result=make_classifier_result(needs_orchestrator=True, category=Category.INFORMATION),
        )

    stage = build_orchestrator_stage(
        "Inspect container",
        make_classifier_result(needs_orchestrator=True, category=Category.INFORMATION),
        conversation_id=f"conv-ev-{detail_key}",
        orchestrator_fn=_orchestrator,
        raw_tools=[{"name": "container_inspect"}],  # non-empty → should_run_orchestrator_for_frame=True
    )

    details = stage.thinking_context[detail_key]
    assert len(details) == 1
    assert details[0]["capability_evidence_types"] == ["thermal_scan"]
