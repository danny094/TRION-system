"""Regressionstests für core/task_loop/progress_utterance_builder.py — P9.

Prüft:
- tool_start → progress_utterance
- tool_result success/fail/timeout → progress_utterance
- task_loop_state WAITING/REPLANNING/BLOCKED → progress_utterance
- task_loop_state COMPLETED/EXECUTING → None (kein Progress)
- text enthält niemals Tool-Ergebnisinhalt
"""
from __future__ import annotations

from core.task_loop.progress_utterance_builder import build_progress_utterance


# ── T1: tool_start → progress_utterance ──────────────────────────────────────

def test_tool_start_emits_progress():
    """T1: tool_start ergibt generischen Fortschritt ohne interne IDs."""
    result = build_progress_utterance({
        "type": "tool_start",
        "tool_name": "deploy_container",
        "step_id": "step-1",
    })
    assert result is not None
    assert result["type"] == "progress_utterance"
    assert result["trigger_event"] == "tool_start"
    assert "deploy_container" not in result["text"]
    assert "tool_name" not in result
    assert "step_id" not in result


# ── T2: tool_result success → progress_utterance ─────────────────────────────

def test_tool_result_success_emits_progress():
    """T2: tool_result success=True enthält nur generischen Fortschritt."""
    result = build_progress_utterance({
        "type": "tool_result",
        "tool_name": "memory_search_fts",
        "step_id": "step-2",
        "status": "success",
        "success": True,
        "output_keys": ["items", "count"],
    })
    assert result is not None
    assert result["type"] == "progress_utterance"
    assert result["trigger_event"] == "tool_result"
    assert "memory_search_fts" not in result["text"]
    # kein Ergebnisinhalt
    assert "items" not in result["text"]
    assert "count" not in result["text"]


# ── T3: tool_result failure → progress_utterance ─────────────────────────────

def test_tool_result_failure_emits_progress():
    """T3: tool_result success=False, kein Timeout → text 'fehlgeschlagen'."""
    result = build_progress_utterance({
        "type": "tool_result",
        "tool_name": "deploy_container",
        "step_id": "step-3",
        "status": "failed",
        "success": False,
        "error": "container_not_found",
    })
    assert result is not None
    assert "fehlgeschlagen" in result["text"]
    # error-Inhalt nicht in text
    assert "container_not_found" not in result["text"]


# ── T4: tool_result timeout → text 'Timeout' ─────────────────────────────────

def test_tool_result_timeout_emits_timeout_text():
    """T4: status='timeout' → text enthält 'Timeout'."""
    result = build_progress_utterance({
        "type": "tool_result",
        "tool_name": "slow_tool",
        "step_id": "step-4",
        "status": "timeout",
        "success": False,
    })
    assert result is not None
    assert "Timeout" in result["text"]


# ── T5: task_loop_state WAITING → progress_utterance ─────────────────────────

def test_task_loop_state_waiting_emits_progress():
    """T5: state='waiting', step_title='Deploy' → text enthält 'Freigabe' und/oder 'Deploy'."""
    result = build_progress_utterance({
        "type": "task_loop_state",
        "state": "waiting",
        "step_title": "Deploy",
        "step_id": "step-5",
    })
    assert result is not None
    assert result["type"] == "progress_utterance"
    assert result["trigger_event"] == "task_loop_state"
    assert "Freigabe" in result["text"]
    assert "Deploy" not in result["text"]


# ── T6: task_loop_state REPLANNING → progress_utterance ──────────────────────

def test_task_loop_state_replanning_emits_progress():
    """T6: state='replanning' → text enthält 'neu'."""
    result = build_progress_utterance({
        "type": "task_loop_state",
        "state": "replanning",
        "step_title": "Backup erstellen",
    })
    assert result is not None
    assert "neu" in result["text"]


# ── T7: task_loop_state BLOCKED → progress_utterance ─────────────────────────

def test_task_loop_state_blocked_emits_progress():
    """T7: state='blocked' → text enthält 'Blockiert'."""
    result = build_progress_utterance({
        "type": "task_loop_state",
        "state": "blocked",
        "step_title": "Cleanup",
        "stop_reason": "capability_gap",
    })
    assert result is not None
    assert "Blockiert" in result["text"]
    assert result.get("stop_reason") == "capability_gap"


# ── T8: task_loop_state COMPLETED → None ─────────────────────────────────────

def test_task_loop_state_completed_returns_none():
    """T8: state='completed' → None (kein Progress-Event)."""
    result = build_progress_utterance({
        "type": "task_loop_state",
        "state": "completed",
        "step_title": "Done",
    })
    assert result is None


# ── T9: task_loop_state EXECUTING → None ─────────────────────────────────────

def test_task_loop_state_executing_returns_none():
    """T9: state='executing' → None (Progress kommt via tool_start)."""
    result = build_progress_utterance({
        "type": "task_loop_state",
        "state": "executing",
        "step_title": "Deploy",
    })
    assert result is None


# ── T10: text enthält nie output_keys / result-Inhalte ───────────────────────

def test_progress_text_never_contains_result_content():
    """T10: output_keys aus tool_result erscheinen nicht in progress text."""
    result = build_progress_utterance({
        "type": "tool_result",
        "tool_name": "memory_search_fts",
        "step_id": "step-10",
        "status": "success",
        "success": True,
        "output_keys": ["secret_key", "sensitive_data", "internal_result"],
    })
    assert result is not None
    text = result["text"]
    assert "secret_key" not in text
    assert "sensitive_data" not in text
    assert "internal_result" not in text


# ── Zusatz: unbekannter Event-Typ → None ─────────────────────────────────────

def test_unknown_event_type_returns_none():
    """Unbekannter Event-Typ → None, kein Fehler."""
    result = build_progress_utterance({"type": "workspace_update", "data": "x"})
    assert result is None


def test_empty_event_returns_none():
    """Leeres Dict → None."""
    result = build_progress_utterance({})
    assert result is None
