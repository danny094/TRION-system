"""Explicit local browser origins consumed by Admin CORS and auth guards."""
import os
from urllib.parse import urlsplit


_DEFAULT_ORIGINS = (
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:8400",
    "http://localhost:8400",
)


def get_allowed_origins() -> tuple[str, ...]:
    raw = os.getenv("TRION_ALLOWED_ORIGINS", "").strip()
    origins = tuple(item.strip().rstrip("/") for item in raw.split(",") if item.strip())
    result = origins or _DEFAULT_ORIGINS
    for origin in result:
        try:
            parsed = urlsplit(origin)
            local = (
                parsed.scheme == "http"
                and parsed.hostname in {"127.0.0.1", "localhost"}
                and parsed.port is not None
                and not parsed.username
                and not parsed.password
                and parsed.path in {"", "/"}
                and not parsed.query
                and not parsed.fragment
            )
        except ValueError:
            local = False
        if not local:
            raise ValueError("CORS origins must be explicit local HTTP origins")
    return tuple(dict.fromkeys(result))


ALLOW_ORIGINS = list(get_allowed_origins())
ALLOWED_ORIGINS = ",".join(ALLOW_ORIGINS)
ENABLE_CORS = os.getenv("ENABLE_CORS", "true").lower() == "true"
