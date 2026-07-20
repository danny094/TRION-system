"""Grounding-State lesen/schreiben fuer den Pipeline-Runner.

Eine Aufgabe: kapselt get_recent_grounding_state()/remember_grounding_state()
inklusive der zugehoerigen TTL-Config an einer Stelle, statt die TTL-Werte an
zwei Aufrufstellen in core/pipeline/runner.py zu wiederholen.

Reine Verdrahtung, keine eigene Logik, kein LLM-Call.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from config import get_grounding_state_ttl_s, get_grounding_state_ttl_turns
from core.output.grounding_state import get_recent_grounding_state, remember_grounding_state


def inject_recent_grounding_state(orchestrator_context: Any, recent_grounding_state: Optional[Dict[str, Any]]) -> None:
    """Schreibt recent_grounding_state in den verschachtelten Orchestrator-Context (Shadow Mode)."""
    if not recent_grounding_state:
        return
    orchestrator = orchestrator_context.get("orchestrator") if isinstance(orchestrator_context, dict) else None
    inner = orchestrator.get("context") if isinstance(orchestrator, dict) and isinstance(orchestrator.get("context"), dict) else None
    if inner is not None:
        inner["grounding_state"] = recent_grounding_state


def resolve_grounding_state(conversation_id: str, history_len: int) -> Optional[Dict[str, Any]]:
    return get_recent_grounding_state(
        conversation_id=conversation_id,
        history_len=history_len,
        ttl_s=get_grounding_state_ttl_s(),
        ttl_turns=get_grounding_state_ttl_turns(),
    )


def persist_grounding_state(
    *,
    conversation_id: str,
    history_len: int,
    grounded_results: List[Any],
) -> None:
    if not grounded_results:
        return
    remember_grounding_state(
        conversation_id=conversation_id,
        history_len=history_len,
        grounded_results=grounded_results,
    )
