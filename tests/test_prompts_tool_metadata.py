"""Regressionstest: _tools_json() injiziert Tool-Metadaten für das Modell.

Prompt-Provenance (Doc 36 Regel 5): tool_role, capability_risk, capability_operation,
capability_required_args kommen aus tool_intents.json via tool_runner_bridge._tool_intent_for()
→ core/orchestrator/tool_descriptor_projection.descriptor_from_raw() → orchestrator_stage.py Tool-Details.
Nur nicht-leere Werte werden serialisiert.
"""
from __future__ import annotations

import json

from core.orchestrator.contracts import ToolDescriptor
from core.thinking.prompts import build_thinking_prompt


def _descriptor(
    name: str = "memory_save",
    tool_role: str = "primary",
    capability_risk: str = "mutating",
    capability_operation: str = "save",
    capability_required_args: list[str] | None = None,
) -> ToolDescriptor:
    return ToolDescriptor(
        name=name,
        description="Save a fact to memory.",
        source="memory-mcp",
        capability_domain="memory",
        capability_operation=capability_operation,
        capability_entity_types=[],
        capability_evidence_types=["memory_write_confirmation"],
        capability_required_args=capability_required_args or ["key", "value"],
        capability_risk=capability_risk,
        capability_target_scopes=[],
        tool_role=tool_role,
        intent_description="",
        intent_keywords=[],
    )


def _parse_tools_from_prompt(prompt: str) -> list[dict]:
    """Extrahiert den tools-JSON-Block aus dem thinking_available_tools-Abschnitt."""
    marker = "VERFÜGBARE TOOLS (Vorausgewählt):"
    idx = prompt.find(marker)
    if idx == -1:
        return []
    section = prompt[idx + len(marker):].strip()
    start = section.find("[")
    end = section.find("]", start) + 1
    # Wähle den äußersten ]-Block (mehrzeiliges JSON-Array)
    depth, pos = 0, start
    for i, ch in enumerate(section[start:], start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return json.loads(section[start:end])


def test_tools_json_includes_metadata_fields():
    tool = _descriptor()
    prompt = build_thinking_prompt("Speichere einen Fakt.", available_tools=[tool])
    tools = _parse_tools_from_prompt(prompt)
    assert len(tools) == 1
    entry = tools[0]
    assert entry["tool_role"] == "primary"
    assert entry["capability_risk"] == "mutating"
    assert entry["capability_operation"] == "save"
    assert entry["capability_required_args"] == ["key", "value"]


def test_tools_json_skips_empty_metadata():
    tool = _descriptor(tool_role="", capability_risk="", capability_operation="")
    prompt = build_thinking_prompt("Test.", available_tools=[tool])
    tools = _parse_tools_from_prompt(prompt)
    assert len(tools) == 1
    entry = tools[0]
    assert "tool_role" not in entry
    assert "capability_risk" not in entry
    assert "capability_operation" not in entry


def test_tools_json_mapping_also_gets_metadata():
    tool = {
        "name": "memory_search",
        "description": "Search memory.",
        "mcp": "memory-mcp",
        "tool_role": "primary",
        "capability_risk": "read",
        "capability_operation": "semantic_search",
        "capability_required_args": ["query"],
    }
    prompt = build_thinking_prompt("Suche.", available_tools=[tool])
    tools = _parse_tools_from_prompt(prompt)
    assert len(tools) == 1
    entry = tools[0]
    assert entry["tool_role"] == "primary"
    assert entry["capability_risk"] == "read"
    assert entry["capability_required_args"] == ["query"]
