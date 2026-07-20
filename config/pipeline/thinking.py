"""
config.pipeline.thinking
=======================
Thinking-Layer Analysepfad und LLM-Aufrufsteuerung.
"""
import os

from config.infra.adapter import settings


def get_thinking_analyzer_enable() -> bool:
    return settings.get(
        "THINKING_ANALYZER_ENABLE",
        os.getenv("THINKING_ANALYZER_ENABLE", "false"),
    ).lower() == "true"


def get_thinking_timeout_s() -> float:
    return float(settings.get("THINKING_TIMEOUT_S", os.getenv("THINKING_TIMEOUT_S", "45")))


def get_thinking_context_item_cap() -> int:
    return int(settings.get("THINKING_CONTEXT_ITEM_CAP", os.getenv("THINKING_CONTEXT_ITEM_CAP", "3")))


def get_thinking_context_char_cap() -> int:
    return int(settings.get("THINKING_CONTEXT_CHAR_CAP", os.getenv("THINKING_CONTEXT_CHAR_CAP", "1200")))


THINKING_ANALYZER_ENABLE = get_thinking_analyzer_enable()
THINKING_TIMEOUT_S = get_thinking_timeout_s()
THINKING_CONTEXT_ITEM_CAP = get_thinking_context_item_cap()
THINKING_CONTEXT_CHAR_CAP = get_thinking_context_char_cap()
