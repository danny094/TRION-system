"""One-call DeepSeek trace for the Filesystem and TaskLoop boundary."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import subprocess
import time

from tests.p11_live_http import post_chat_events
from tests.test_deepseek_backend_live import (
    assert_no_ollama_fallback,
    require_deepseek_backend,
)

PROMPT = "Kannst du kurz prüfen, ob es im Workspace eine status.txt gibt?"
CONVERSATION_ID = "p11-r6-memory-taskloop-trace-once"
EXPECTED_CONTEXT_TOOLS = (
    "conversation_meta_get",
    "memory_search_fts",
    "memory_search_layered",
    "memory_semantic_search",
    "memory_recent",
)
def _by_type(events: list[dict], event_type: str) -> list[dict]:
    return [event for event in events if event.get("type") == event_type]


def _effective_value(effective: dict, key: str):
    value = effective.get(key)
    return value.get("value") if isinstance(value, dict) else value


def _docker_logs_since(started_at: datetime) -> list[str]:
    since = started_at.isoformat().replace("+00:00", "Z")
    result = subprocess.run(
        ["docker", "logs", "--since", since, "--tail", "2000", "trion-admin-api"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in (result.stdout + result.stderr).splitlines() if line]


def _mcp_calls(lines: list[str]) -> list[str]:
    known = (*EXPECTED_CONTEXT_TOOLS, "filesystem_list")
    return [
        tool_name
        for line in lines
        for tool_name in known
        if f"Calling {tool_name} via " in line
    ]


def test_deepseek_workspace_traces_memory_context_and_task_loop_completion():
    live = require_deepseek_backend()
    effective = live["effective"]
    model = live["model"]
    providers = {
        role: str(_effective_value(effective, role) or "").lower()
        for role in ("THINKING_PROVIDER", "CONTROL_PROVIDER", "OUTPUT_PROVIDER")
    }
    assert model, "No effective DeepSeek model configured."
    assert set(providers.values()) == {"deepseek"}, providers

    started_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    events = post_chat_events(
        provider="deepseek",
        model=model,
        conversation_id=CONVERSATION_ID,
        messages=[{"role": "user", "content": PROMPT}],
    )
    assert_no_ollama_fallback(events)
    time.sleep(1)
    log_lines = _docker_logs_since(started_at)
    mcp_calls = _mcp_calls(log_lines)
    tool_starts = _by_type(events, "tool_start")
    tool_results = _by_type(events, "tool_result")
    task_states = _by_type(events, "task_loop_state")
    final_state = task_states[-1] if task_states else {}
    done = (_by_type(events, "done") or [{}])[-1]
    findings = []
    expected_mcp_calls = [*EXPECTED_CONTEXT_TOOLS, "filesystem_list"]
    if mcp_calls != expected_mcp_calls:
        findings.append(f"runtime_mcp_call_drift:{mcp_calls}")
    filesystem_owner_lines = [
        line for line in log_lines if "Calling filesystem_list via filesystem" in line
    ]
    if len(filesystem_owner_lines) != 1:
        findings.append(f"filesystem_owner_drift:{len(filesystem_owner_lines)}")
    if len(tool_starts) != 1:
        findings.append(f"tool_start_count_drift:{len(tool_starts)}")
    if len(tool_results) != 1 or tool_results[0].get("status") != "success":
        findings.append(f"filesystem_tool_result_status:{tool_results}")
    elif tool_results[0].get("success") is not True or tool_results[0].get("artifact_count") != 2:
        findings.append(f"filesystem_tool_result_shape:{tool_results[0]}")
    state_names = [str(event.get("state") or "") for event in task_states]
    if state_names != ["executing", "completed"]:
        findings.append(f"task_loop_state_drift:{state_names}")
    if any(event.get("stop_reason") is not None for event in task_states):
        findings.append(f"task_loop_stop_reason_drift:{task_states}")
    if final_state.get("state") != "completed" or final_state.get("stop_reason") is not None:
        findings.append(
            f"task_loop_{final_state.get('state') or 'missing'}:"
            f"{final_state.get('stop_reason') or 'no_stop_reason'}"
        )
    replan_traces = _by_type(events, "replan_trace")
    if replan_traces:
        findings.append(f"unexpected_replan:{replan_traces}")
    if done.get("done_reason") != "stop":
        findings.append(f"done_reason:{done.get('done_reason') or 'missing'}")
    final_content = [
        str(event.get("content") or "")
        for event in events
        if event.get("type") == "final_content"
    ]
    if len(final_content) != 1 or "status.txt" not in final_content[0] or "17 Bytes" not in final_content[0]:
        findings.append(f"final_content_drift:{final_content}")
    if "missing_endpoint:ollama" in str(events).lower():
        findings.append("ollama_fallback_visible")

    trace = {
        "prompt": PROMPT,
        "conversation_id": CONVERSATION_ID,
        "model": model,
        "providers": providers,
        "runtime_mcp_calls": mcp_calls,
        "classifier_events": _by_type(events, "classifier_result"),
        "routing_events": _by_type(events, "routing_trace"),
        "thinking_events": _by_type(events, "thinking_plan"),
        "tool_starts": tool_starts,
        "tool_results": tool_results,
        "task_loop_states": task_states,
        "task_loop_provenance": _by_type(events, "task_loop_provenance"),
        "replan_traces": replan_traces,
        "done": done,
        "final_content": final_content,
        "findings": findings,
    }
    print("\n[P11-R6-Memory-TaskLoop-Trace] " + json.dumps(trace, sort_keys=True))
    assert findings == [], trace


if __name__ == "__main__":
    test_deepseek_workspace_traces_memory_context_and_task_loop_completion()
