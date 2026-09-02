from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.responses import JSONResponse


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API = ROOT / "adapters" / "admin-api"
MAIN = ADMIN_API / "main.py"
if str(ADMIN_API) not in sys.path:
    sys.path.insert(0, str(ADMIN_API))

from security_contracts import AuthenticatedPrincipal, MiddlewareConfig, PrincipalKind
from security_middleware import SecurityMiddleware
from security_routes import LoginRequest
from memory.embedding.config import MEMORY_READ_ROUTES


TEST_SESSION = "TEST-ONLY-browser-session"
TEST_RESOLVE = "TEST-ONLY-resolve-token"
TEST_MEMORY = "TEST-ONLY-memory-token"
TEST_CSRF = "TEST-ONLY-session-csrf"
LOCAL_ORIGIN = "http://localhost:3000"


class _Authority:
    def __init__(self, *, provisioned: bool = True) -> None:
        self.provisioned = provisioned

    def is_provisioned(self) -> bool:
        return self.provisioned

    def authenticate_session(self, token: str) -> AuthenticatedPrincipal | None:
        if token != TEST_SESSION:
            return None
        return AuthenticatedPrincipal("admin", PrincipalKind.BROWSER, TEST_CSRF)

    def authenticate_service(self, token: str) -> AuthenticatedPrincipal | None:
        kinds = {
            TEST_RESOLVE: PrincipalKind.SECRET_RESOLVE,
            TEST_MEMORY: PrincipalKind.MEMORY_READ,
        }
        kind = kinds.get(token)
        return AuthenticatedPrincipal(kind.value, kind) if kind else None


def _app(authority: _Authority, observed: list[str]) -> FastAPI:
    app = FastAPI()
    config = MiddlewareConfig("trion_session", "x-trion-csrf", (LOCAL_ORIGIN,))
    app.add_middleware(SecurityMiddleware, authority=authority, config=config)

    @app.get("/health")
    async def health() -> dict[str, str]:
        observed.append("health")
        return {"status": "ok"}

    @app.post("/api/auth/login")
    async def login_checker(_body: LoginRequest) -> JSONResponse:
        observed.append("credential-checker")
        return JSONResponse({"error": "AUTH_NOT_PROVISIONED"}, status_code=503)

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def protected(path: str) -> dict[str, str]:
        observed.append(path)
        return {"status": "handled"}

    return app


async def _asgi_request(app: FastAPI, method: str, path: str, headers: dict[str, str] | None = None) -> int:
    sent: list[dict] = []
    consumed = False

    async def receive() -> dict:
        nonlocal consumed
        if not consumed:
            consumed = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()],
        "client": ("127.0.0.1", 40000),
        "server": ("127.0.0.1", 8200),
    }
    await app(scope, receive, send)
    return next(message["status"] for message in sent if message["type"] == "http.response.start")


def _request(app: FastAPI, method: str, path: str, headers: dict[str, str] | None = None) -> int:
    return asyncio.run(_asgi_request(app, method, path, headers))


def test_health_is_live_but_unprovisioned_state_blocks_before_handlers() -> None:
    observed: list[str] = []
    app = _app(_Authority(provisioned=False), observed)

    assert _request(app, "GET", "/health") == 200
    assert _request(app, "GET", "/api/settings") == 503
    assert observed == ["health"]


def test_product_app_installs_global_security_before_router_dispatch() -> None:
    source = MAIN.read_text(encoding="utf-8")

    security = source.index("app.add_middleware(SecurityMiddleware")
    first_router = source.index("app.include_router(")
    assert security < first_router
    assert "allowed_origins = get_allowed_origins()" in source
    assert "allow_origins=list(allowed_origins)" in source
    assert 'allow_origins=["*"]' not in source and "allow_origins=['*']" not in source


def test_only_exact_login_path_reaches_credential_checker_unprovisioned() -> None:
    observed: list[str] = []
    app = _app(_Authority(provisioned=False), observed)

    assert _request(app, "POST", "/api/auth/login") == 503
    assert _request(app, "GET", "/api/auth/login") == 503
    assert _request(app, "POST", "/api/auth/login/extra") == 503
    assert observed == []

    provisioned = _app(_Authority(), [])
    assert _request(provisioned, "POST", "/api/auth/login") == 403
    assert _request(
        provisioned, "POST", "/api/auth/login", {"origin": "http://attacker.invalid"}
    ) == 403


def test_browser_cookie_and_session_bound_origin_csrf_guard_mutations() -> None:
    observed: list[str] = []
    app = _app(_Authority(), observed)
    cookie = {"cookie": f"trion_session={TEST_SESSION}"}
    invalid_cookie = {"cookie": "trion_session=TEST-ONLY-invalid"}
    no_cookie = {"origin": LOCAL_ORIGIN, "x-trion-csrf": TEST_CSRF}

    assert _request(app, "GET", "/api/settings") == 401
    assert _request(app, "GET", "/api/settings", invalid_cookie) == 401
    assert _request(app, "POST", "/api/settings", no_cookie) == 401
    assert _request(app, "GET", "/api/settings", cookie) == 200
    assert _request(app, "POST", "/api/settings", cookie) == 403
    assert _request(
        app,
        "POST",
        "/api/settings",
        {**cookie, "origin": "http://attacker.invalid", "x-trion-csrf": TEST_CSRF},
    ) == 403
    assert _request(
        app,
        "POST",
        "/api/settings",
        {**cookie, "origin": LOCAL_ORIGIN, "x-trion-csrf": "TEST-ONLY-wrong"},
    ) == 403
    assert _request(
        app,
        "POST",
        "/api/settings",
        {**cookie, "origin": LOCAL_ORIGIN, "x-trion-csrf": TEST_CSRF},
    ) == 200
    assert observed == ["api/settings", "api/settings"]


def test_service_tokens_are_exact_route_method_scoped_and_not_cross_usable() -> None:
    observed: list[str] = []
    app = _app(_Authority(), observed)

    def bearer(token: str) -> dict[str, str]:
        return {"authorization": f"Bearer {token}"}

    resolve = "/api/secrets/resolve/OPENAI_API_KEY"
    memory_paths = tuple(sorted(MEMORY_READ_ROUTES))
    assert _request(app, "GET", resolve, {"cookie": f"trion_session={TEST_SESSION}"}) == 401
    assert _request(app, "GET", resolve, bearer(TEST_RESOLVE)) == 200
    assert all(_request(app, "GET", path, bearer(TEST_MEMORY)) == 200 for path in memory_paths)
    assert _request(app, "POST", resolve, bearer(TEST_RESOLVE)) == 403
    assert _request(app, "GET", memory_paths[0], bearer(TEST_RESOLVE)) == 403
    assert _request(app, "GET", resolve, bearer(TEST_MEMORY)) == 403
    assert _request(app, "GET", memory_paths[0] + "/extra", bearer(TEST_MEMORY)) == 403
    assert _request(app, "GET", "/api/settings", bearer(TEST_MEMORY)) == 403
    assert observed == [resolve.lstrip("/"), *(path.lstrip("/") for path in memory_paths)]
