from __future__ import annotations

from types import ModuleType

from core.llm.provider_registry import (
    PROVIDER_VALUES,
    anthropic_base,
    get_provider_spec,
    looks_cross_provider_model_name,
    minimax_base,
    normalize_provider,
    ollama_cloud_base,
    ollama_cloud_model_candidates,
    openrouter_base,
    openai_base,
    provider_ids,
    provider_order_map,
    provider_preset_models,
    provider_preset_models_env_key,
    provider_secret_names,
    resolve_role_provider,
)
from . import anthropic, minimax, ollama_cloud, ollama_local, openai, openrouter


def provider_runtime_module(provider: str) -> ModuleType:
    provider_norm = normalize_provider(provider)
    spec = get_provider_spec(provider_norm)
    if spec.api_style == "ollama_local":
        return ollama_local
    if spec.api_style == "ollama_cloud":
        return ollama_cloud
    if spec.api_style == "openai":
        return openai
    if spec.api_style == "openrouter":
        return openrouter
    if spec.api_style == "minimax":
        return minimax
    return anthropic


__all__ = [
    "PROVIDER_VALUES",
    "anthropic",
    "anthropic_base",
    "looks_cross_provider_model_name",
    "minimax",
    "minimax_base",
    "normalize_provider",
    "ollama_cloud",
    "ollama_cloud_base",
    "ollama_cloud_model_candidates",
    "ollama_local",
    "openai",
    "openrouter",
    "openrouter_base",
    "openai_base",
    "provider_ids",
    "provider_order_map",
    "provider_preset_models",
    "provider_preset_models_env_key",
    "provider_runtime_module",
    "provider_secret_names",
    "resolve_role_provider",
]
