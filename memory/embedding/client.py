import hashlib
import logging
import os
from typing import List, Optional

import requests

from .config import OLLAMA_URL, _ROUTING_LOG_LEVEL
from .model_resolver import _resolve_embedding_model
from .runtime_config import _resolve_runtime_config, _canonical_policy, _resolve_embedding_role_route
from .route_resolver import _inline_resolve_target

logger = logging.getLogger(__name__)


def compute_embedding_version_id(model: str, runtime_policy: str) -> str:
    """Deterministische Versions-ID: Hash aus model + runtime policy."""
    seed = f"{(model or '').strip()}|{(runtime_policy or 'auto').strip().lower()}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"embv1_{digest}"


def get_active_embedding_version() -> str:
    """Aktive embedding_version auf Basis der effektiven Runtime-Konfiguration."""
    return compute_embedding_version_id(_resolve_embedding_model(), _canonical_policy())


def _env_first(*names: str) -> str:
    for name in names:
        value = str(os.getenv(name, "")).strip()
        if value:
            return value
    return ""


def _embedding_headers(url: str) -> dict:
    normalized = str(url or "").rstrip("/").lower()
    if "ollama.com" not in normalized:
        return {}
    api_key = _env_first("OLLAMA_API_KEY", "OLLAMA_CLOUD_API_KEY", "OLLAMA_KEY", "OLLAMA")
    if not api_key:
        logger.error("[Embedding] Missing Ollama Cloud API key")
        return {}
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _request_embedding_v1(url: str, model: str, text: str, options: dict) -> Optional[List[float]]:
    payload: dict = {"model": model, "input": text.strip()}
    if options:
        payload["options"] = options
    resp = requests.post(f"{str(url).rstrip('/')}/api/embed", json=payload, headers=_embedding_headers(url) or None, timeout=30)
    resp.raise_for_status()
    embeddings = resp.json().get("embeddings") or []
    if embeddings and isinstance(embeddings[0], list):
        return embeddings[0]
    return None


def _request_embedding_legacy(url: str, model: str, text: str, options: dict) -> Optional[List[float]]:
    payload: dict = {"model": model, "prompt": text.strip()}
    if options:
        payload["options"] = options
    resp = requests.post(f"{str(url).rstrip('/')}/api/embeddings", json=payload, headers=_embedding_headers(url) or None, timeout=30)
    resp.raise_for_status()
    return resp.json().get("embedding") or None


def _request_embedding(url: str, model: str, text: str, options: dict) -> Optional[List[float]]:
    """Einzelner Ollama embedding Call. Bevorzugt /api/embed, faellt auf /api/embeddings zurueck."""
    try:
        return _request_embedding_v1(url, model, text, options)
    except requests.HTTPError as exc:
        status = int(getattr(getattr(exc, "response", None), "status_code", 0) or 0)
        if status != 404:
            logger.error(f"[Embedding] Error @ {url}/api/embed: {exc}")
            return None
    except Exception as exc:
        logger.error(f"[Embedding] Error @ {url}/api/embed: {exc}")
        return None
    try:
        return _request_embedding_legacy(url, model, text, options)
    except Exception as e:
        logger.error(f"[Embedding] Error @ {url}/api/embeddings: {e}")
        return None


def _log_routing_decision(message: str, hard_error: bool = False) -> None:
    if hard_error:
        logger.error(message)
        return
    if _ROUTING_LOG_LEVEL == "info":
        logger.info(message)
        return
    if _ROUTING_LOG_LEVEL == "error":
        logger.error(message)
        return
    logger.warning(message)


def get_embedding(text: str) -> Optional[List[float]]:
    """Holt Embedding-Vektor von Ollama. Routes GPU/CPU per embedding_runtime_policy."""
    if not text or not text.strip():
        return None

    model = _resolve_embedding_model()
    rt = _resolve_runtime_config()
    role_route = _resolve_embedding_role_route()

    requested_pin = (role_route or {}).get("requested_target", "auto") if role_route else "auto"
    if role_route and requested_pin != "auto":
        if role_route.get("hard_error"):
            logger.error(
                f"[Embedding] role=sql_memory_embedding "
                f"policy={rt.get('embedding_runtime_policy') or rt['EMBEDDING_EXECUTION_MODE']} "
                f"requested_target={requested_pin} effective_target=none fallback=true "
                f"reason={role_route.get('fallback_reason') or 'requested_unavailable'}"
            )
            return None
        eff_target = role_route.get("effective_target") or requested_pin
        endpoint = role_route.get("endpoint") or OLLAMA_URL
        options = {"num_gpu": 0} if eff_target == "cpu" and endpoint == OLLAMA_URL else {}
        target = {
            "requested_policy": rt.get("embedding_runtime_policy") or rt["EMBEDDING_EXECUTION_MODE"],
            "requested_target": requested_pin,
            "effective_target": eff_target,
            "fallback_reason": role_route.get("fallback_reason"),
            "hard_error": False, "error_code": None,
            "endpoint": endpoint, "options": options, "fallback_endpoint": None,
            "fallback_policy": rt["EMBEDDING_FALLBACK_POLICY"],
            "reason": f"layer_routing_pin:{requested_pin}", "target": eff_target,
        }
    else:
        target = _inline_resolve_target(
            mode=rt.get("embedding_runtime_policy") or rt["EMBEDDING_EXECUTION_MODE"],
            endpoint_mode=rt["EMBEDDING_ENDPOINT_MODE"],
            base_endpoint=OLLAMA_URL,
            gpu_endpoint=rt["EMBEDDING_GPU_ENDPOINT"],
            cpu_endpoint=rt["EMBEDDING_CPU_ENDPOINT"],
            fallback_policy=rt["EMBEDDING_FALLBACK_POLICY"],
        )

    _log_msg = (
        f"[Embedding] role=sql_memory_embedding "
        f"policy={target['requested_policy']} "
        f"requested_target={target['requested_target']} "
        f"effective_target={target['effective_target'] or 'none'} "
        f"fallback={target['fallback_reason'] is not None} "
        f"reason={target['reason']}"
    )
    if target["hard_error"]:
        _log_routing_decision(_log_msg, hard_error=True)
        return None
    _log_routing_decision(_log_msg, hard_error=False)

    embedding = _request_embedding(target["endpoint"], model, text, target["options"])
    if embedding is None and target.get("fallback_endpoint"):
        logger.info(
            f"[Embedding] role=sql_memory_embedding policy={target['requested_policy']} "
            f"primary_failed=true retrying_fallback={target['fallback_endpoint']}"
        )
        embedding = _request_embedding(target["fallback_endpoint"], model, text, target["options"])

    if embedding:
        logger.info(f"[Embedding] Generated vector with {len(embedding)} dimensions target={target['effective_target']}")
        return embedding
    logger.error("[Embedding] No embedding in response")
    return None


def get_embedding_with_metadata(text: str) -> Optional[dict]:
    """Embedding plus Versions-Metadaten (model, dim, version, policy)."""
    embedding = get_embedding(text)
    if not embedding:
        return None
    model = _resolve_embedding_model()
    policy = _canonical_policy()
    return {
        "embedding": embedding,
        "embedding_model": model,
        "embedding_dim": len(embedding),
        "embedding_version": compute_embedding_version_id(model, policy),
        "runtime_policy": policy,
    }


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Cosine Similarity zwischen zwei Vektoren. Gibt 0.0 bei leerem/ungleichem Input zurück."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    n1 = sum(a * a for a in vec1) ** 0.5
    n2 = sum(b * b for b in vec2) ** 0.5
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)
