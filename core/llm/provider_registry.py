from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple

from config import get_control_provider, get_output_model, get_output_provider, get_thinking_provider


ProviderApiStyle = Literal["ollama_local", "ollama_cloud", "openai", "anthropic", "openrouter", "minimax"]


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    label: str
    api_style: ProviderApiStyle
    order: int
    secret_names: Tuple[str, ...] = ()
    default_base_url: str = ""
    base_url_env_keys: Tuple[str, ...] = ()
    preset_models: Tuple[str, ...] = ()
    preset_models_env_key: str = ""


PROVIDER_SPECS: Dict[str, ProviderSpec] = {
    "ollama": ProviderSpec(id="ollama", label="Ollama", api_style="ollama_local", order=0),
    "ollama_cloud": ProviderSpec(
        id="ollama_cloud",
        label="Ollama Cloud",
        api_style="ollama_cloud",
        order=1,
        secret_names=("OLLAMA_API_KEY", "OLLAMA_CLOUD_API_KEY", "OLLAMA_KEY", "OLLAMA"),
        default_base_url="https://ollama.com",
        base_url_env_keys=("OLLAMA_CLOUD_BASE", "OLLAMA_API_BASE"),
        preset_models=("llama3.3", "llama3.2", "qwen2.5", "mistral-small3.1", "deepseek-r1"),
        preset_models_env_key="OLLAMA_CLOUD_MODEL_PRESETS",
    ),
    "openai": ProviderSpec(
        id="openai",
        label="OpenAI",
        api_style="openai",
        order=2,
        secret_names=("OPENAI_API_KEY", "OPENAI_KEY"),
        default_base_url="https://api.openai.com/v1",
        base_url_env_keys=("OPENAI_API_BASE",),
        preset_models=("gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini", "o3", "o3-mini"),
        preset_models_env_key="OPENAI_MODEL_PRESETS",
    ),
    "anthropic": ProviderSpec(
        id="anthropic",
        label="Anthropic",
        api_style="anthropic",
        order=3,
        secret_names=("ANTHROPIC_API_KEY", "CLAUDE_API_KEY", "ANTHROPIC_KEY"),
        default_base_url="https://api.anthropic.com/v1",
        base_url_env_keys=("ANTHROPIC_API_BASE",),
        preset_models=("claude-sonnet-4-5", "claude-3-7-sonnet-latest", "claude-3-5-haiku-latest"),
        preset_models_env_key="ANTHROPIC_MODEL_PRESETS",
    ),
    "openrouter": ProviderSpec(
        id="openrouter",
        label="OpenRouter",
        api_style="openrouter",
        order=4,
        secret_names=("OPENROUTER_API_KEY", "OPENROUTER_KEY"),
        default_base_url="https://openrouter.ai/api/v1",
        base_url_env_keys=("OPENROUTER_API_BASE",),
        preset_models=("openai/gpt-4o-mini", "anthropic/claude-3.5-haiku", "google/gemini-2.5-flash"),
        preset_models_env_key="OPENROUTER_MODEL_PRESETS",
    ),
    "deepseek": ProviderSpec(
        id="deepseek",
        label="DeepSeek",
        api_style="openai",
        order=5,
        secret_names=("DEEPSEEK_API_KEY", "DEEPSEEK_KEY", "DEEPSEEK"),
        default_base_url="https://api.deepseek.com",
        base_url_env_keys=("DEEPSEEK_API_BASE",),
        preset_models=("deepseek-v4-flash", "deepseek-v4-pro"),
        preset_models_env_key="DEEPSEEK_MODEL_PRESETS",
    ),
    "minimax": ProviderSpec(
        id="minimax",
        label="MiniMax",
        api_style="minimax",
        order=6,
        secret_names=("MINIMAX_API_KEY", "MINIMAX_KEY"),
        default_base_url="https://api.minimax.io/v1",
        base_url_env_keys=("MINIMAX_API_BASE",),
        preset_models=("MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5", "MiniMax-M2.5-highspeed", "MiniMax-M2.1"),
        preset_models_env_key="MINIMAX_MODEL_PRESETS",
    ),
}

PROVIDER_VALUES = set(PROVIDER_SPECS.keys())


def get_provider_spec(provider: str, default: str = "ollama") -> ProviderSpec:
    provider_norm = normalize_provider(provider, default=default)
    return PROVIDER_SPECS[provider_norm]


def provider_ids() -> List[str]:
    return list(PROVIDER_SPECS.keys())


def provider_order_map() -> Dict[str, int]:
    return {provider_id: spec.order for provider_id, spec in PROVIDER_SPECS.items()}


def provider_secret_names(provider: str) -> Tuple[str, ...]:
    return get_provider_spec(provider).secret_names


def provider_default_base(provider: str) -> str:
    return get_provider_spec(provider).default_base_url


def provider_base(provider: str) -> str:
    spec = get_provider_spec(provider)
    for env_key in spec.base_url_env_keys:
        value = str(os.getenv(env_key, "")).strip().rstrip("/")
        if value:
            return value
    return str(spec.default_base_url).rstrip("/")


def provider_preset_models(provider: str) -> Tuple[str, ...]:
    return get_provider_spec(provider).preset_models


def provider_preset_models_env_key(provider: str) -> str:
    return get_provider_spec(provider).preset_models_env_key


def normalize_provider(raw: str, default: str = "ollama") -> str:
    provider = str(raw or "").strip().lower()
    return provider if provider in PROVIDER_VALUES else default


def resolve_role_provider(role: str, default: str = "ollama") -> str:
    role_norm = str(role or "").strip().lower()
    if role_norm == "thinking":
        return normalize_provider(get_thinking_provider(), default=default)
    if role_norm == "control":
        return normalize_provider(get_control_provider(), default=default)
    if role_norm == "output":
        return normalize_provider(get_output_provider(), default=default)
    return normalize_provider(default, default="ollama")


def openai_base() -> str:
    return provider_base("openai")


def anthropic_base() -> str:
    return provider_base("anthropic")


def ollama_cloud_base() -> str:
    return provider_base("ollama_cloud")


def openrouter_base() -> str:
    return provider_base("openrouter")


def minimax_base() -> str:
    return provider_base("minimax")


def looks_cross_provider_model_name(model_name: str) -> bool:
    low = str(model_name or "").strip().lower()
    if low.startswith("gpt-oss"):
        return False
    return bool(low) and (
        low.startswith("gpt-") or low.startswith("o1") or low.startswith("o3")
        or low.startswith("o4") or low.startswith("claude")
    )


def ollama_cloud_model_candidates(requested_model: str) -> List[str]:
    preferred = str(requested_model or "").strip()
    output_model = str(get_output_model() or "").strip()
    out: List[str] = []

    if looks_cross_provider_model_name(preferred):
        if output_model:
            out.append(output_model)
        if preferred and preferred not in out:
            out.append(preferred)
    else:
        if preferred:
            out.append(preferred)
        if output_model and output_model not in out:
            out.append(output_model)
    return out or [preferred]
