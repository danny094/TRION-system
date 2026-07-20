import os
import logging

logger = logging.getLogger(__name__)

_ROUTING_LOG_LEVEL = str(
    os.getenv("EMBEDDING_ROUTING_LOG_LEVEL", "warning")
).strip().lower()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

SETTINGS_API_URL = os.getenv("SETTINGS_API_URL", "").strip()
if not SETTINGS_API_URL:
    _admin_api = os.getenv(
        "ADMIN_API_URL",
        os.getenv("TRION_ADMIN_API_URL", "http://trion-admin-api:8200"),
    ).rstrip("/")
    SETTINGS_API_URL = f"{_admin_api}/api/settings"

_EMBED_DEFAULT = os.getenv("EMBEDDING_MODEL", "hellord/mxbai-embed-large-v1:f16")
_CACHE_TTL = int(os.getenv("SETTINGS_CACHE_TTL", "60"))
_RUNTIME_CACHE_TTL = int(
    os.getenv("SETTINGS_RUNTIME_CACHE_TTL", os.getenv("SETTINGS_CACHE_TTL", "5"))
)
_RUNTIME_REFRESH_INTERVAL_S = max(
    2,
    int(os.getenv("SETTINGS_RUNTIME_REFRESH_INTERVAL_S", "15")),
)
_RUNTIME_FETCH_TIMEOUT_S = max(
    0.2,
    float(os.getenv("SETTINGS_RUNTIME_FETCH_TIMEOUT_S", "1.5")),
)
_ROUTE_FETCH_TIMEOUT_S = max(
    0.2,
    float(os.getenv("SETTINGS_ROUTE_FETCH_TIMEOUT_S", "1.0")),
)
_REFRESH_WARN_THROTTLE_S = 60.0

_RT_DEFAULTS = {
    "EMBEDDING_EXECUTION_MODE": "auto",
    "EMBEDDING_FALLBACK_POLICY": "best_effort",
    "EMBEDDING_GPU_ENDPOINT": "",
    "EMBEDDING_CPU_ENDPOINT": "",
    "EMBEDDING_ENDPOINT_MODE": "single",
}


def _runtime_api_base() -> str:
    """Leitet API-Base aus SETTINGS_API_URL ab (.../api/settings → .../api/runtime/...)."""
    if not SETTINGS_API_URL:
        return ""
    marker = "/api/settings"
    idx = SETTINGS_API_URL.find(marker)
    if idx >= 0:
        return SETTINGS_API_URL[:idx]
    return SETTINGS_API_URL.rstrip("/")
