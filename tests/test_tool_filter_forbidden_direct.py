"""Regressionstest: filter_tools() entfernt Tools mit tool_role=forbidden_direct.

Guard-Anforderung (Doc 36 Regel 3): Tools mit tool_role=forbidden_direct dürfen
nie die Planning-Fläche erreichen, unabhängig von allowlist/blocklist.
Kein hardcodierter Tool-Name (Doc 36 Regel 2): Filterung liest aus tool.tool_role.
"""
from __future__ import annotations

from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_filter import filter_tools


def _tool(name: str, tool_role: str = "primary") -> ToolDescriptor:
    return ToolDescriptor(
        name=name,
        description="",
        source="",
        capability_domain="",
        capability_operation="",
        capability_entity_types=[],
        capability_evidence_types=[],
        capability_required_args=[],
        capability_risk="",
        capability_target_scopes=[],
        tool_role=tool_role,
        intent_description="",
        intent_keywords=[],
    )


def test_forbidden_direct_removed_without_blocklist():
    tools = [_tool("graph_find_duplicate_nodes", tool_role="forbidden_direct")]
    result = filter_tools(tools, allowlist=[], blocklist=[])
    assert result == []


def test_forbidden_direct_removed_even_if_in_allowlist():
    forbidden = _tool("graph_merge_nodes", tool_role="forbidden_direct")
    result = filter_tools([forbidden], allowlist=["graph_merge_nodes"], blocklist=[])
    assert result == []


def test_primary_role_passes_through():
    tool = _tool("memory_save", tool_role="primary")
    result = filter_tools([tool], allowlist=[], blocklist=[])
    assert result == [tool]


def test_supporting_role_passes_through():
    tool = _tool("memory_search", tool_role="supporting")
    result = filter_tools([tool], allowlist=[], blocklist=[])
    assert result == [tool]


def test_mixed_list_only_removes_forbidden():
    allowed = _tool("memory_save", tool_role="primary")
    forbidden = _tool("graph_find_duplicate_nodes", tool_role="forbidden_direct")
    result = filter_tools([allowed, forbidden], allowlist=[], blocklist=[])
    assert result == [allowed]
