"""Shared CoreChatRequest-Factory fuer die P0-Core-Pipeline-Tests.

Basisslice-, Task-Loop- und Long-Document-Tests teilen sich denselben
minimalen Request-Aufbau - hier einmal definiert, statt in jeder
gesplitteten Datei dupliziert.
"""

from __future__ import annotations

from core.models import CoreChatRequest, Message, MessageRole


def core_pipeline_request(text: str = "Was ist der Status?") -> CoreChatRequest:
    return CoreChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content=text)],
        conversation_id="p0-test",
        source_adapter="pytest",
    )
