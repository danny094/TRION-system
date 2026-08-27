"""
Models Routes — catalog, tags, provider helpers.
"""
import os
from typing import Dict, List

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.llm.provider_registry import provider_base, provider_ids, provider_order_map, provider_preset_models, provider_preset_models_env_key
from utils.logger import log_error

router = APIRouter()

_MODEL_PROVIDER_ORDER = provider_order_map()
_OPENROUTER_RECOMMENDED = {
    "openrouter/auto",
    "openai/gpt-4o-mini",
    "anthropic/claude-3.5-haiku",
    "google/gemini-2.5-flash",
    "qwen/qwen3-coder",
}


def _dedupe(items: List[str]) -> List[str]:
    seen, out = set(), []
    for raw in items:
        name = str(raw or "").strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            out.append(name)
    return out


def _parse_model_env(key: str, defaults: List[str]) -> List[str]:
    raw = str(os.getenv(key, "")).strip()
    if not raw:
        return _dedupe(defaults)
    return _dedupe([p.strip() for p in raw.split(",")]) or _dedupe(defaults)


async def _fetch_tags(endpoint: str, headers: dict = None) -> List[Dict]:
    base = str(endpoint or "").strip().rstrip("/")
    if not base:
        return []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{base}/api/tags", headers=headers or None)
            resp.raise_for_status()
            payload = resp.json() if resp.content else {}
        rows = payload.get("models", []) if isinstance(payload, dict) else []
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


async def _fetch_openai_compatible_models(endpoint: str, headers: dict = None) -> List[Dict]:
    base = str(endpoint or "").strip().rstrip("/")
    if not base:
        return []
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(f"{base}/models", headers=headers or None)
            resp.raise_for_status()
            payload = resp.json() if resp.content else {}
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


@router.get("/api/models/catalog")
async def models_catalog():
    from config import OLLAMA_BASE
    from core.llm_provider_client import _resolve_cloud_api_key
    from core.llm.provider_registry import minimax_base, openrouter_base
    from utils.settings import ALLOWED_MODEL_KEYS, get_effective_model_settings
    from utils.routing.role_endpoint import resolve_ollama_base_endpoint
    from utils.settings import settings as runtime_settings

    persisted = {k: v for k, v in getattr(runtime_settings, "settings", {}).items() if k in ALLOWED_MODEL_KEYS}
    effective = get_effective_model_settings(persisted)
    selected_model = str(effective.get("OUTPUT_MODEL", {}).get("value") or "").strip()
    selected_provider = str(effective.get("OUTPUT_PROVIDER", {}).get("value") or "ollama").strip().lower()
    if selected_provider not in _MODEL_PROVIDER_ORDER:
        selected_provider = "ollama"

    rows: List[Dict] = []
    seen: set = set()

    def add(name: str, provider: str, source: str, size: int = None, category: str | None = None):
        n = str(name or "").strip()
        p = provider if provider in _MODEL_PROVIDER_ORDER else "ollama"
        key = f"{p}::{n.lower()}"
        if not n or key in seen:
            return
        seen.add(key)
        item: Dict = {"name": n, "provider": p, "source": source,
                      "selected": n.lower() == selected_model.lower() and p == selected_provider}
        if size and int(size) > 0:
            item["size"] = int(size)
        if category:
            item["category"] = category
        rows.append(item)

    local_ep = resolve_ollama_base_endpoint(default_endpoint=OLLAMA_BASE)
    for m in await _fetch_tags(local_ep):
        add(str(m.get("name", "") if isinstance(m, dict) else m), "ollama", "local",
            int(m.get("size", 0)) if isinstance(m, dict) else None)

    cloud_base = str(os.getenv("OLLAMA_CLOUD_BASE", os.getenv("OLLAMA_API_BASE", "https://ollama.com"))).strip().rstrip("/")
    cloud_key = await _resolve_cloud_api_key("ollama_cloud")
    cloud_headers = {"Authorization": f"Bearer {cloud_key}"} if cloud_key else {}
    for m in await _fetch_tags(cloud_base, cloud_headers):
        add(str(m.get("name", "") if isinstance(m, dict) else m), "ollama_cloud", "cloud",
            int(m.get("size", 0)) if isinstance(m, dict) else None)

    openrouter_key = await _resolve_cloud_api_key("openrouter")
    openrouter_headers = {"Authorization": f"Bearer {openrouter_key}"} if openrouter_key else {}
    for m in await _fetch_openai_compatible_models(openrouter_base(), openrouter_headers):
        if not isinstance(m, dict):
            continue
        model_id = str(m.get("id", "") or m.get("name", "")).strip()
        architecture = m.get("architecture", {}) if isinstance(m.get("architecture"), dict) else {}
        outputs = architecture.get("output_modalities", []) if isinstance(architecture.get("output_modalities"), list) else []
        if outputs and "text" not in [str(v).strip().lower() for v in outputs]:
            continue
        category = "recommended" if model_id in _OPENROUTER_RECOMMENDED else "all"
        add(model_id, "openrouter", "cloud", category=category)

    deepseek_key = await _resolve_cloud_api_key("deepseek")
    deepseek_headers = {"Authorization": f"Bearer {deepseek_key}"} if deepseek_key else {}
    if deepseek_key:
        for m in await _fetch_openai_compatible_models(provider_base("deepseek"), deepseek_headers):
            if not isinstance(m, dict):
                continue
            add(str(m.get("id", "") or m.get("name", "")), "deepseek", "cloud")

    minimax_key = await _resolve_cloud_api_key("minimax")
    minimax_headers = {"Authorization": f"Bearer {minimax_key}"} if minimax_key else {}
    for m in await _fetch_openai_compatible_models(minimax_base(), minimax_headers):
        if not isinstance(m, dict):
            continue
        add(str(m.get("id", "") or m.get("name", "")), "minimax", "cloud")

    for provider_id in provider_ids():
        preset_env_key = provider_preset_models_env_key(provider_id)
        preset_defaults = list(provider_preset_models(provider_id))
        if not preset_env_key or not preset_defaults:
            continue
        for name in _parse_model_env(preset_env_key, preset_defaults):
            category = "recommended" if provider_id == "openrouter" and name in _OPENROUTER_RECOMMENDED else None
            add(name, provider_id, "preset", category=category)
    if selected_model:
        add(selected_model, selected_provider, "configured")

    rows.sort(key=lambda r: (0 if r.get("selected") else 1,
                             _MODEL_PROVIDER_ORDER.get(r.get("provider", ""), 99),
                             r.get("name", "").lower()))
    return JSONResponse({
        "models": rows,
        "effective": {"OUTPUT_MODEL": selected_model, "OUTPUT_PROVIDER": selected_provider},
        "providers": provider_ids(),
    })


@router.get("/api/tags")
async def tags():
    from config import OLLAMA_BASE
    from utils.routing.role_endpoint import resolve_ollama_base_endpoint
    try:
        ep = resolve_ollama_base_endpoint(default_endpoint=OLLAMA_BASE)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{ep}/api/tags")
            resp.raise_for_status()
            return JSONResponse(resp.json())
    except Exception as e:
        log_error(f"[Tags] Error: {e}")
        return JSONResponse({"models": []})
