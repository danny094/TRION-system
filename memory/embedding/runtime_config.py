import os
import time
import threading
import requests
from typing import Optional, Dict, Any

from .config import (
    ADMIN_API_URL,
    COMPUTE_ROUTING_ROUTE,
    EMBEDDINGS_RUNTIME_ROUTE,
    _RT_DEFAULTS,
    _RUNTIME_FETCH_TIMEOUT_S,
    _ROUTE_FETCH_TIMEOUT_S,
    _RUNTIME_REFRESH_INTERVAL_S,
    _REFRESH_WARN_THROTTLE_S,
    _memory_read_headers,
)

_rt_cache: dict = {"config": None, "ts": 0.0}
_route_cache: dict = {"value": None, "ts": 0.0}
_refresh_state = {"started": False, "lock": threading.Lock()}
_warn_state: dict = {"runtime": 0.0, "route": 0.0}


def _default_runtime_config() -> dict:
    cfg = {k: os.getenv(k, v) for k, v in _RT_DEFAULTS.items()}
    cfg["embedding_runtime_policy"] = os.getenv(
        "EMBEDDING_RUNTIME_POLICY",
        os.getenv("EMBEDDING_EXECUTION_MODE", "auto"),
    )
    if not cfg.get("embedding_runtime_policy"):
        cfg["embedding_runtime_policy"] = (
            str(cfg.get("EMBEDDING_EXECUTION_MODE", "auto")).strip().lower() or "auto"
        )
    return cfg


def _warn_throttled(kind: str, msg: str) -> None:
    now = time.time()
    if (now - float(_warn_state.get(kind, 0.0))) < _REFRESH_WARN_THROTTLE_S:
        return
    _warn_state[kind] = now
    import logging
    logging.getLogger(__name__).warning(msg)


def _refresh_runtime_config_once() -> None:
    cfg = _default_runtime_config()
    if ADMIN_API_URL:
        try:
            resp = requests.get(
                f"{ADMIN_API_URL}{EMBEDDINGS_RUNTIME_ROUTE}",
                headers=_memory_read_headers(),
                timeout=_RUNTIME_FETCH_TIMEOUT_S,
            )
            resp.raise_for_status()
            data = resp.json()
            effective = data.get("effective", {})
            for key in _RT_DEFAULTS:
                val = effective.get(key, {}).get("value", "")
                if val:
                    cfg[key] = val
            active = str(data.get("runtime", {}).get("active_policy", "")).strip().lower()
            eff_pol = str(
                effective.get("embedding_runtime_policy", {}).get("value", "")
            ).strip().lower()
            if active:
                cfg["embedding_runtime_policy"] = active
            elif eff_pol:
                cfg["embedding_runtime_policy"] = eff_pol
        except Exception as e:
            _warn_throttled("runtime", f"[Embedding] runtime settings refresh failed: {e}")
    _rt_cache["config"] = cfg
    _rt_cache["ts"] = time.time()


def _refresh_route_once() -> None:
    base = ADMIN_API_URL
    if not base:
        _route_cache["value"] = None
        _route_cache["ts"] = time.time()
        return
    try:
        resp = requests.get(
            f"{base}{COMPUTE_ROUTING_ROUTE}",
            headers=_memory_read_headers(),
            timeout=_ROUTE_FETCH_TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()
        emb = (data.get("effective", {}) or {}).get("embedding", {}) or {}
        requested = str(emb.get("requested_target") or "auto").strip()
        endpoint = emb.get("effective_endpoint")
        _route_cache["value"] = {
            "requested_target": requested,
            "effective_target": emb.get("effective_target"),
            "endpoint": endpoint,
            "fallback_reason": emb.get("fallback_reason"),
            "hard_error": bool(requested != "auto" and not endpoint),
        }
        _route_cache["ts"] = time.time()
    except Exception as e:
        _warn_throttled("route", f"[Embedding] runtime route refresh failed: {e}")


def _runtime_refresh_loop() -> None:
    while True:
        try:
            _refresh_runtime_config_once()
            _refresh_route_once()
        except Exception:
            pass
        time.sleep(_RUNTIME_REFRESH_INTERVAL_S)


def _ensure_runtime_refresh_worker() -> None:
    if _refresh_state["started"]:
        return
    with _refresh_state["lock"]:
        if _refresh_state["started"]:
            return
        thread = threading.Thread(
            target=_runtime_refresh_loop,
            daemon=True,
            name="embedding-runtime-refresh",
        )
        thread.start()
        _refresh_state["started"] = True


def _resolve_runtime_config() -> dict:
    _ensure_runtime_refresh_worker()
    cfg = _rt_cache.get("config")
    if isinstance(cfg, dict):
        return cfg
    _refresh_runtime_config_once()
    cfg = _rt_cache.get("config")
    if isinstance(cfg, dict):
        return cfg
    cfg = _default_runtime_config()
    _rt_cache["config"] = cfg
    _rt_cache["ts"] = time.time()
    return cfg


def _canonical_policy(runtime_cfg: Optional[dict] = None) -> str:
    cfg = runtime_cfg or _resolve_runtime_config()
    return str(
        cfg.get("embedding_runtime_policy") or cfg.get("EMBEDDING_EXECUTION_MODE") or "auto"
    ).strip().lower()


def _resolve_embedding_role_route() -> Optional[Dict[str, Any]]:
    """Gibt gecachte Compute-Route für embedding-Rolle zurück."""
    _ensure_runtime_refresh_worker()
    route = _route_cache.get("value")
    return route if isinstance(route, dict) else None


# Cold-start: einmalig synchron auflösen damit erster Request keine ENV-Defaults bekommt
try:
    _resolve_runtime_config()
except Exception:
    pass
