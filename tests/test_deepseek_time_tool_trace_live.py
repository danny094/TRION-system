"""One-call DeepSeek trace for the time-tool eligibility boundary."""
from __future__ import annotations

import json
from pathlib import Path

from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_eligibility import eligible_tools_for_contract
from tests.p11_live_http import get_json, post_chat_events
from tests.test_deepseek_backend_live import (
    assert_no_ollama_fallback,
    require_deepseek_backend,
)

ROOT = Path(__file__).resolve().parents[1]
PROMPT = "Wie spät ist es gerade ungefähr?"


def _time_intent() -> dict:
    payload = json.loads(
        (ROOT / "examples/time_mcp_bundle/tool_intents.json").read_text(
            encoding="utf-8"
        )
    )
    return next(item for item in payload["tools"] if item["name"] == "time_now")


def _descriptor(intent: dict, *, evidence_types: list[str]) -> ToolDescriptor:
    return ToolDescriptor(
        name=str(intent["name"]),
        description=str(intent.get("description") or ""),
        source="time-mcp",
        capability_domain=str(intent.get("domain") or ""),
        capability_operation=str(intent.get("operation") or ""),
        capability_evidence_types=list(evidence_types),
        capability_target_scopes=list(intent.get("target_scopes") or []),
        capability_risk=str(intent.get("risk") or ""),
        tool_role=str(intent.get("tool_role") or "primary"),
    )


def _event(events: list[dict], event_type: str) -> dict:
    return next((event for event in events if event.get("type") == event_type), {})


def test_deepseek_time_request_traces_bundle_eligibility_divergence():
    live = require_deepseek_backend()
    catalog = get_json("/api/tools", timeout=10)
    catalog_names = {
        str(item.get("name"))
        for item in catalog.get("tools", [])
        if isinstance(item, dict)
    }
    assert "time_now" in catalog_names

    events = post_chat_events(
        provider="deepseek",
        model=live["model"],
        conversation_id="deepseek-time-eligibility-trace",
        messages=[{"role": "user", "content": PROMPT}],
    )
    assert_no_ollama_fallback(events)

    classifier_result = _event(events, "classifier_result")
    routing = _event(events, "routing_trace")
    thinking = _event(events, "thinking_plan")
    done = _event(events, "done")
    tool_starts = [event for event in events if event.get("type") == "tool_start"]
    intent = _time_intent()
    contract = {
        "domain": str(intent.get("domain") or ""),
        "primary_operation": routing.get("operation"),
        "allowed_operations": routing.get("allowed_operations"),
        "required_evidence": routing.get("required_evidence"),
        "mutating_action": False,
    }
    declared_evidence = list(intent.get("evidence_types") or [])
    actual_eligible = eligible_tools_for_contract(
        [_descriptor(intent, evidence_types=declared_evidence)], contract
    )
    counterfactual_eligible = eligible_tools_for_contract(
        [_descriptor(intent, evidence_types=["live_runtime"])], contract
    )
    trace = {
        "prompt": PROMPT,
        "classifier_result": classifier_result,
        "bundle_evidence_types": declared_evidence,
        "routing_operation": routing.get("operation"),
        "routing_required_evidence": routing.get("required_evidence"),
        "actual_eligible": [tool.name for tool in actual_eligible],
        "counterfactual_eligible": [tool.name for tool in counterfactual_eligible],
        "thinking_needs_task_loop": thinking.get("needs_task_loop"),
        "tool_start_count": len(tool_starts),
        "done_reason": done.get("done_reason"),
    }
    print("\n[DeepSeek-Time-Eligibility-Trace] " + json.dumps(trace, sort_keys=True))

    assert trace == {
        **trace,
        "bundle_evidence_types": ["live_runtime"],
        "routing_operation": "read",
        "routing_required_evidence": ["live_runtime"],
        "actual_eligible": ["time_now"],
        "counterfactual_eligible": ["time_now"],
        "thinking_needs_task_loop": True,
        "tool_start_count": 1,
        "done_reason": "stop",
    }, trace
