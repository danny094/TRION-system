"""Regressionstest: Home-Synonyme in resolve_step_tool_arguments.

Wenn der Text auf den Home-Container verweist (z. B. 'im Homespace', 'zuhause',
'in diesem Container') und home_context.verified=True, muss container_id direkt
aus home_context aufgelöst werden — kein container <name> Regex nötig.
"""
from __future__ import annotations

from core.thinking.runtime_arguments import resolve_step_tool_arguments

_TOOL_DETAIL = {
    "capability_required_args": ["container_id_or_name"],
    "capability_operation": "inspect",
}

_HOME_CTX = {
    "context": {
        "home_context": {
            "container_id": "abc-123",
            "container_name": "trion-home",
            "verified": True,
        }
    }
}


def _resolve(user_text: str, ctx=_HOME_CTX):
    return resolve_step_tool_arguments(
        "container_inspect",
        user_text,
        _TOOL_DETAIL,
        ctx,
    )


def test_homespace_synonym_resolves_to_home_container_id():
    args = _resolve("Prüfe den Status im Homespace.")
    assert args.get("container_id") == "abc-123"


def test_zuhause_synonym_resolves_to_home_container_id():
    args = _resolve("Was läuft gerade zuhause?")
    assert args.get("container_id") == "abc-123"


def test_dieser_container_resolves_to_home_container_id():
    args = _resolve("Inspect this container.")
    assert args.get("container_id") == "abc-123"


def test_home_synonym_without_verified_falls_back_to_name():
    """Ohne verified=True kein Shortcut — normaler Pfad."""
    ctx = {
        "context": {
            "home_context": {
                "container_id": "abc-123",
                "container_name": "trion-home",
                "verified": False,
            }
        }
    }
    args = _resolve("Prüfe trion-home.", ctx=ctx)
    # trion-home Literal wird via _extract_container_name erkannt + Name-Match → container_id
    assert args.get("container_id") == "abc-123"


def test_unknown_text_returns_empty_args():
    args = _resolve("Gib mir die aktuelle Uhrzeit.")
    assert args == {}


def test_trion_home_literal_still_works():
    args = _resolve("Führe container_inspect auf trion-home aus.")
    assert args.get("container_id") == "abc-123"
