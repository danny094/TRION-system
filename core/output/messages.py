from typing import Any, Dict, List

from core.models import CoreChatRequest, MessageRole
from core.output.prompts import build_output_system_prompt

_MAX_HISTORY_TURNS = 10


def build_output_messages(
    output_request: Any,
    chat_request: CoreChatRequest,
) -> List[Dict[str, str]]:
    system_prompt = build_output_system_prompt(
        thinking_plan=output_request.thinking_plan,
        context=output_request.context if isinstance(output_request.context, dict) else {},
    )

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    history = _recent_history(chat_request)
    messages.extend(history)

    return messages


def _recent_history(chat_request: CoreChatRequest) -> List[Dict[str, str]]:
    turns: List[Dict[str, str]] = []
    for msg in chat_request.messages:
        if msg.role == MessageRole.SYSTEM:
            continue
        turns.append(msg.to_dict())

    if len(turns) <= _MAX_HISTORY_TURNS * 2:
        return turns

    # Keep the last N turns (user+assistant pairs) plus always the last user message
    return turns[-(  _MAX_HISTORY_TURNS * 2):]
