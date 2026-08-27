"""Offline contract test for the canonical Time MCP intent."""
from pathlib import Path

from core.classifier.classifier import classify
from core.orchestrator.orchestrator import orchestrate
from core.routing_frame.builder import build_routing_frame
from mcp.installer_tool_intents import build_tool_intent_mirror

ROOT = Path(__file__).resolve().parents[1]
PROMPT = "Wie spät ist es gerade ungefähr?"


def _time_tool() -> dict:
    intent_path = ROOT / "examples/time_mcp_bundle/tool_intents.json"
    mirror = build_tool_intent_mirror(intent_path, bundle_version="1.0.0")
    intent = next(item for item in mirror["tools"] if item["name"] == "time_now")
    return {
        "name": "time_now",
        "description": intent["description"],
        "mcp": "time-mcp",
        "tool_intent": intent,
    }


def test_canonical_time_bundle_satisfies_live_runtime_contract():
    classifier = classify(PROMPT)
    routing_frame = build_routing_frame(PROMPT, classifier)
    package = orchestrate(
        PROMPT,
        classifier,
        raw_tools=[_time_tool()],
        routing_frame=routing_frame,
    )

    assert routing_frame["operation_contract"]["primary_operation"] == "read"
    assert routing_frame["operation_contract"]["required_evidence"] == ("live_runtime",)
    assert [tool.name for tool in package.available_tools] == ["time_now"]
    assert [tool.name for tool in package.selected_tools] == ["time_now"]
