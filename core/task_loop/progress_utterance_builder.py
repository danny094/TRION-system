"""Deterministischer Builder für progress_utterance Events.

Nimmt einen bekannten Runtime-Event-Dict und gibt ein progress_utterance-Payload
zurück oder None (für Events ohne sichtbaren Fortschrittstext).

Kein LLM-Call. Keine Importe außerhalb von core/task_loop/.
Invariante: text enthält niemals Tool-Ergebnisinhalte.
"""
from __future__ import annotations

from typing import Any, Dict

# Zustände, die ein progress_utterance erzeugen (task_loop_state)
_PROGRESS_STATES = frozenset({"waiting", "replanning", "blocked"})


def build_progress_utterance(event: Dict[str, Any]) -> Dict[str, Any] | None:
    """Erzeugt ein progress_utterance-Payload aus einem Runtime-Event oder gibt None zurück.

    Args:
        event: Roher Event-Dict (tool_start / tool_result / task_loop_state),
               optional mit "step_title" angereichert.

    Returns:
        progress_utterance-Payload-Dict oder None.
    """
    event_type = str(event.get("type") or "")

    if event_type == "tool_start":
        return _from_tool_start(event)
    if event_type == "tool_result":
        return _from_tool_result(event)
    if event_type == "task_loop_state":
        return _from_task_loop_state(event)
    return None


def _from_tool_start(event: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "progress_utterance",
        "text": "Führe Werkzeugschritt aus …",
        "trigger_event": "tool_start",
    }


def _from_tool_result(event: Dict[str, Any]) -> Dict[str, Any]:
    status = str(event.get("status") or "")
    success = bool(event.get("success", False))

    if status == "timeout":
        text = "Werkzeugschritt: Timeout."
    elif success:
        text = "Werkzeugschritt erfolgreich abgeschlossen."
    else:
        text = "Werkzeugschritt fehlgeschlagen."

    return {
        "type": "progress_utterance",
        "text": text,
        "trigger_event": "tool_result",
    }


def _from_task_loop_state(event: Dict[str, Any]) -> Dict[str, Any] | None:
    state = str(event.get("state") or "")
    if state not in _PROGRESS_STATES:
        return None

    stop_reason = str(event.get("stop_reason") or "")

    if state == "waiting":
        text = "Warte auf Freigabe."
    elif state == "replanning":
        text = "Plane neu."
    else:  # blocked
        text = "Blockiert."

    payload: Dict[str, Any] = {
        "type": "progress_utterance",
        "text": text,
        "trigger_event": "task_loop_state",
    }
    if stop_reason:
        payload["stop_reason"] = stop_reason
    return payload
