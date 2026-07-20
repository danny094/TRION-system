"""
Compatibility facade for the TRION LLM package.

New code should import from `core.llm`. This module keeps the historical
`core.llm_provider_client` import path stable while the implementation lives in
small provider-focused modules.
"""
from __future__ import annotations

from core.llm.chat import complete_chat
from core.llm.messages import (
    flatten_content as _flatten_content,
    normalize_anthropic_messages as _normalize_anthropic_messages,
    normalize_openai_messages as _normalize_openai_messages,
)
from core.llm.prompts import complete_prompt, stream_prompt
from core.llm.providers import (
    PROVIDER_VALUES as _PROVIDER_VALUES,
    anthropic_base as _anthropic_base,
    looks_cross_provider_model_name as _looks_cross_provider_model_name,
    normalize_provider,
    ollama_cloud_base as _ollama_cloud_base,
    ollama_cloud_model_candidates as _ollama_cloud_model_candidates,
    openai_base as _openai_base,
    resolve_role_provider,
)
from core.llm.rate_limits import (
    capture_rate_limit_headers as _capture_rate_limit_headers,
    get_rate_limit_snapshot,
)
from core.llm.secrets import API_KEY_CACHE as _API_KEY_CACHE
from core.llm.secrets import resolve_cloud_api_key as _resolve_cloud_api_key
from core.llm.streaming import stream_chat, stream_chat_events

__all__ = [
    "_API_KEY_CACHE",
    "_PROVIDER_VALUES",
    "_anthropic_base",
    "_capture_rate_limit_headers",
    "_flatten_content",
    "_looks_cross_provider_model_name",
    "_normalize_anthropic_messages",
    "_normalize_openai_messages",
    "_ollama_cloud_base",
    "_ollama_cloud_model_candidates",
    "_openai_base",
    "_resolve_cloud_api_key",
    "complete_chat",
    "complete_prompt",
    "get_rate_limit_snapshot",
    "normalize_provider",
    "resolve_role_provider",
    "stream_chat",
    "stream_chat_events",
    "stream_prompt",
]
