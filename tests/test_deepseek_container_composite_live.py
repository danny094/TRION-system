"""Gated DeepSeek evidence for the P11 container list-to-logs contract."""
from __future__ import annotations

from datetime import datetime, timezone
import os
import re
import subprocess
import time

import pytest

from tests.p11_container_prompt_matrix import POSITIVE_CASES, render_prompt
from tests.test_deepseek_workspace_toolstart_trace_live import EXPECTED_CONTEXT_TOOLS
from tests.test_deepseek_piano_taskloop_live import (
    _by_type,
    _live_tools,
    _post_chat,
    live_chat,
)

_FULL_CONTAINER_ID = re.compile(r"[a-f0-9]{64}\Z")
_CONTAINER_NAME = re.compile(
    r"(?![a-f0-9]+\Z)[a-z][a-z0-9_-]*(?:\.[a-z0-9_-]+)*\Z"
)
_RUN_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}\Z")


def _matrix_config() -> tuple[str, str, str]:
    enabled = str(os.environ.get("TRION_ENABLE_DEEPSEEK_CONTAINER_MATRIX", "")).lower()
    if enabled not in {"1", "true", "yes", "on"}:
        pytest.skip("Set TRION_ENABLE_DEEPSEEK_CONTAINER_MATRIX=1 for the 32-call matrix.")
    container_id = str(os.environ.get("TRION_P11_MATRIX_CONTAINER_ID", ""))
    container_name = str(os.environ.get("TRION_P11_MATRIX_CONTAINER_NAME", ""))
    run_id = str(os.environ.get("TRION_P11_MATRIX_RUN_ID", ""))
    assert _FULL_CONTAINER_ID.fullmatch(container_id), "Matrix requires one full lowercase container ID."
    assert _CONTAINER_NAME.fullmatch(container_name), "Matrix requires one safe container name."
    assert _RUN_ID.fullmatch(run_id), "Matrix requires one explicit safe run ID."
    return container_id, container_name, run_id


def _runtime_mcp_calls_since(started_at: datetime, *, expected_count: int) -> list[str]:
    since = started_at.isoformat().replace("+00:00", "Z")
    call_pattern = re.compile(r"\bCalling ([a-zA-Z0-9_.-]+) via ")
    deadline = time.monotonic() + 15
    calls: list[str] = []
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        result = subprocess.run(
            ["docker", "logs", "--since", since, "--tail", "2000", "trion-admin-api"],
            check=True,
            capture_output=True,
            text=True,
            timeout=remaining,
        )
        calls = [
            match.group(1)
            for line in (result.stdout + result.stderr).splitlines()
            if (match := call_pattern.search(line))
        ]
        if len(calls) >= expected_count:
            return calls
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(0.25, remaining))
    return calls


def _assert_matrix_case(
    events: list[dict],
    *,
    case_id: str,
    runtime_mcp_calls: list[str],
) -> None:
    traces = _by_type(events, "routing_trace")
    assert traces, f"{case_id}: routing_trace missing"
    trace = traces[-1]
    assert trace.get("operation") == "list", f"{case_id}: operation drift"
    assert trace.get("allowed_operations") == ["list"], f"{case_id}: allowed operation drift"
    assert trace.get("allowed_transitions") == ["list->logs"], f"{case_id}: transition drift"
    assert trace.get("target_bound") is True, f"{case_id}: target was not bound"

    tool_starts = _by_type(events, "tool_start")
    tool_results = _by_type(events, "tool_result")
    assert len(tool_starts) == 2, f"{case_id}: expected exactly two tool starts"
    assert len(tool_results) == 2, f"{case_id}: expected exactly two tool results"
    assert all(result.get("status") == "success" for result in tool_results), (
        f"{case_id}: unsuccessful tool result"
    )
    assert all(result.get("success") is True for result in tool_results), (
        f"{case_id}: non-success tool projection"
    )
    assert runtime_mcp_calls == [*EXPECTED_CONTEXT_TOOLS, "container_list", "container_logs"], (
        f"{case_id}: runtime MCP call scope or order drift"
    )

    state_names = {state.get("state") for state in _by_type(events, "task_loop_state")}
    assert not state_names.intersection({"replanning", "blocked", "cancelled", "waiting"}), (
        f"{case_id}: unexpected task-loop state"
    )
    done = _by_type(events, "done")
    assert done and done[-1].get("done_reason") == "stop", f"{case_id}: runtime did not stop cleanly"


def test_piano_logzeilen_composite_preserves_list_to_logs(live_chat):
    events = _post_chat(
        conversation_id="piano-logzeilen-composite",
        text="Welche Container laufen und zeige mir die Logzeilen.",
        model=live_chat["model"],
    )
    traces = _by_type(events, "routing_trace")
    assert traces, "Kein routing_trace fuer den Composite-Contract."
    trace = traces[-1]
    assert trace.get("operation") == "list"
    assert trace.get("allowed_operations") == ["list"]
    assert trace.get("allowed_transitions") == ["list->logs"]
    assert _by_type(events, "tool_start"), (
        "Composite-Contract ist sichtbar, aber die initiale list-Operation startet kein Tool."
    )
    assert _by_type(events, "done")[-1].get("done_reason") == "stop"


def test_bilingual_container_prompt_matrix_live(live_chat):
    container_id, container_name, run_id = _matrix_config()
    assert len(POSITIVE_CASES) == 32, "Provider budget drift: matrix must contain exactly 32 cases."
    assert len({case.case_id for case in POSITIVE_CASES}) == 32, (
        "Provider budget drift: matrix case IDs must be unique."
    )
    live_tool_names = {str(tool.get("name")) for tool in _live_tools()}
    assert {"container_list", "container_logs"} <= live_tool_names, (
        "Live catalog does not expose both governed container read tools."
    )

    completed: list[str] = []
    for case in POSITIVE_CASES:
        prompt, _target = render_prompt(
            case,
            container_id=container_id,
            container_name=container_name,
        )
        started_at = datetime.now(timezone.utc)
        events = _post_chat(
            conversation_id=f"{run_id}-{case.case_id}",
            text=prompt,
            model=live_chat["model"],
        )
        runtime_mcp_calls = _runtime_mcp_calls_since(
            started_at,
            expected_count=len(EXPECTED_CONTEXT_TOOLS) + 2,
        )
        _assert_matrix_case(
            events,
            case_id=case.case_id,
            runtime_mcp_calls=runtime_mcp_calls,
        )
        completed.append(case.case_id)
        print(f"[P11-Prompt-Matrix] case={case.case_id} status=PASS")

    assert completed == [case.case_id for case in POSITIVE_CASES]
    print(f"[P11-Prompt-Matrix] completed={len(completed)} status=PASS")
