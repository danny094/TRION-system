from __future__ import annotations

from typing import Any, Dict, Iterable, List

from core.llm.provider_registry import get_provider_spec
from core.llm.providers import normalize_provider, provider_runtime_module
from core.llm.reasoning_sanitizer import sanitize_reasoning_text


async def complete_chat(
    *,
    provider: str,
    model: str,
    messages: Iterable[Dict[str, Any]],
    timeout_s: float = 90.0,
    ollama_endpoint: str = "",
    tools: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    provider_norm = normalize_provider(provider)
    model_name = str(model or "").strip()
    impl = provider_runtime_module(provider_norm)
    kwargs: Dict[str, Any] = {
        "provider": provider_norm,
        "model": model_name,
        "messages": messages,
        "timeout_s": timeout_s,
    }
    if provider_norm in {"ollama", "ollama_cloud"}:
        kwargs["ollama_endpoint"] = ollama_endpoint
    supports_openai_tools = get_provider_spec(provider_norm).api_style == "openai"
    if tools and (provider_norm in {"ollama", "ollama_cloud"} or supports_openai_tools):
        kwargs["tools"] = tools
    result = await impl.complete_chat(**kwargs)
    if isinstance(result, dict):
        result = dict(result)
        result["content"] = sanitize_reasoning_text(str(result.get("content") or ""))
    return result
