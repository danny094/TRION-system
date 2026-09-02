import os
import logging

from config.infra.security import get_memory_read_token_path

logger = logging.getLogger(__name__)

_ROUTING_LOG_LEVEL = str(
    os.getenv("EMBEDDING_ROUTING_LOG_LEVEL", "warning")
).strip().lower()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

_ALLOWED_ADMIN_API_URLS = frozenset(
    {
        "http://trion-admin-api:8200",
        "http://127.0.0.1:8200",
        "http://localhost:8200",
    }
)


def _admin_api_url() -> str:
    settings_url = os.getenv("SETTINGS_API_URL", "").strip().rstrip("/")
    base = settings_url.removesuffix("/api/settings") if settings_url else ""
    candidate = base or os.getenv("ADMIN_API_URL", "http://trion-admin-api:8200").strip().rstrip("/")
    if candidate not in _ALLOWED_ADMIN_API_URLS:
        raise RuntimeError("Admin API URL is outside the local security boundary")
    return candidate


ADMIN_API_URL = _admin_api_url()

MEMORY_READ_TOKEN_FILE = get_memory_read_token_path()
MODELS_EFFECTIVE_ROUTE = "/api/settings/models/effective"
EMBEDDINGS_RUNTIME_ROUTE = "/api/settings/embeddings/runtime"
COMPUTE_ROUTING_ROUTE = "/api/runtime/compute/routing"
MEMORY_READ_ROUTES = frozenset(
    {MODELS_EFFECTIVE_ROUTE, EMBEDDINGS_RUNTIME_ROUTE, COMPUTE_ROUTING_ROUTE}
)

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


def _memory_read_headers() -> dict[str, str]:
    """Read the memory principal token only from its mounted secret file."""
    try:
        token = MEMORY_READ_TOKEN_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError("memory read token unavailable") from exc
    if not token:
        raise RuntimeError("memory read token unavailable")
    return {"Authorization": f"Bearer {token}"}
