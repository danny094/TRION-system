from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API = ROOT / "adapters" / "admin-api"
if str(ADMIN_API) not in sys.path:
    sys.path.insert(0, str(ADMIN_API))

from security_auth import (
    SecurityAuthority,
    SessionCodec,
    SessionRejected,
    hash_credential,
    verify_credential,
)
from security_contracts import (
    AuthenticatedPrincipal, IssuedSession, MiddlewareConfig, PrincipalKind, SecurityPaths,
)
from security_middleware import SecurityMiddleware
from security_routes import LoginRequest, create_security_router


TEST_PASSWORD = "TEST-ONLY-correct-horse"
TEST_SALT = b"TEST-ONLY-salt!"
TEST_SIGNING_KEY = b"TEST-ONLY-session-signing-key!!"
TEST_SESSION = "TEST-ONLY-cookie-token"


class _RouteAuthority:
    ttl_seconds = 60

    def __init__(self) -> None:
        self.provisioned = True
        self.revocations = 0

    def is_provisioned(self) -> bool:
        return self.provisioned

    def verify_password(self, password: str) -> bool:
        return password == TEST_PASSWORD

    def issue_session(self) -> IssuedSession:
        return IssuedSession(TEST_SESSION, TEST_CSRF, 1_060)

    def authenticate_session(self, token: str) -> AuthenticatedPrincipal | None:
        if token != TEST_SESSION or self.revocations:
            return None
        return AuthenticatedPrincipal("admin", PrincipalKind.BROWSER, TEST_CSRF, 1_060)

    def authenticate_service(self, token: str) -> None:
        return None

    def revoke_sessions(self) -> None:
        self.revocations += 1


TEST_CSRF = "TEST-ONLY-session-csrf"


def _route_endpoint(router, path: str, method: str):
    return next(route.endpoint for route in router.routes if route.path == path and method in route.methods)


def test_credentials_use_scrypt_and_constant_contract_verification() -> None:
    encoded = hash_credential(TEST_PASSWORD, salt=TEST_SALT)

    assert encoded.startswith("scrypt$")
    assert TEST_PASSWORD not in encoded
    assert verify_credential(TEST_PASSWORD, encoded) is True
    assert verify_credential("TEST-ONLY-wrong-password", encoded) is False


def test_signed_session_accepts_valid_claims_and_rejects_tamper_and_expiry() -> None:
    codec = SessionCodec(signing_key=TEST_SIGNING_KEY, ttl_seconds=60)
    issued = codec.issue("admin", generation=4, now=1_000, nonce="session-one")

    claims = codec.verify(issued.token, generation=4, now=1_059)
    assert claims.subject == "admin"
    assert claims.generation == 4
    assert claims.expires_at == 1_060
    assert claims.csrf_token == issued.csrf_token

    with pytest.raises(SessionRejected):
        codec.verify(issued.token, generation=4, now=1_060)

    replacement = "A" if issued.token[-1] != "A" else "B"
    with pytest.raises(SessionRejected):
        codec.verify(issued.token[:-1] + replacement, generation=4, now=1_001)
    with pytest.raises(SessionRejected):
        codec.verify(issued.token, generation=4, now=1_061)


def test_generation_rotation_revokes_old_session_and_csrf_is_session_specific() -> None:
    codec = SessionCodec(signing_key=TEST_SIGNING_KEY, ttl_seconds=60)
    first = codec.issue("admin", generation=7, now=2_000, nonce="session-a")
    second = codec.issue("admin", generation=7, now=2_000, nonce="session-b")

    assert first.token != second.token
    assert first.csrf_token != second.csrf_token
    assert codec.verify(first.token, generation=7, now=2_001).csrf_token == first.csrf_token
    assert codec.verify(second.token, generation=7, now=2_001).csrf_token == second.csrf_token

    with pytest.raises(SessionRejected):
        codec.verify(first.token, generation=8, now=2_001)


def test_real_authority_revocation_invalidates_an_issued_session(tmp_path: Path) -> None:
    paths = SecurityPaths(
        tmp_path / "credential.hash", tmp_path / "session.key",
        tmp_path / "resolve.token", tmp_path / "memory.token",
    )
    paths.session_key.write_bytes(TEST_SIGNING_KEY)
    paths.session_generation.write_text("0\n", encoding="ascii")
    authority = SecurityAuthority(paths, ttl_seconds=60)
    issued = authority.issue_session()

    assert authority.authenticate_session(issued.token) is not None
    authority.revoke_sessions()
    assert paths.session_generation.read_text(encoding="ascii") == "1\n"
    assert authority.authenticate_session(issued.token) is None


def test_auth_routes_bind_cookie_metadata_session_projection_and_logout() -> None:
    authority = _RouteAuthority()
    router = create_security_router(authority, cookie_name="trion_session", cookie_secure=False)
    login = _route_endpoint(router, "/api/auth/login", "POST")
    session = _route_endpoint(router, "/api/auth/session", "GET")
    logout = _route_endpoint(router, "/api/auth/logout", "POST")

    invalid = asyncio.run(login(LoginRequest(password="TEST-ONLY-wrong")))
    assert invalid.status_code == 401
    assert json.loads(invalid.body) == {"error": "AUTH_INVALID_CREDENTIAL"}

    success = asyncio.run(login(LoginRequest(password=TEST_PASSWORD)))
    cookie = success.headers["set-cookie"].lower()
    payload = json.loads(success.body)
    assert success.status_code == 200
    assert all(item in cookie for item in ("httponly", "samesite=strict", "path=/", "max-age=60"))
    assert payload == {"principal": "admin", "expires_at": 1_060, "csrf_token": TEST_CSRF}
    assert "TEST-ONLY-cookie-token" not in success.body.decode()

    request = Request({
        "type": "http",
        "state": {"auth_principal": AuthenticatedPrincipal(
            "admin", PrincipalKind.BROWSER, TEST_CSRF, 1_060
        )},
    })
    projected = asyncio.run(session(request))
    assert json.loads(projected.body) == payload

    closed = asyncio.run(logout())
    assert authority.revocations == 1
    assert "trion_session=" in closed.headers["set-cookie"].lower()
    assert "max-age=0" in closed.headers["set-cookie"].lower()

    authority.provisioned = False
    blocked = asyncio.run(login(LoginRequest(password=TEST_PASSWORD)))
    assert blocked.status_code == 503
    assert json.loads(blocked.body) == {"error": "AUTH_NOT_PROVISIONED"}


def test_auth_routes_run_through_global_session_origin_and_csrf_middleware() -> None:
    authority = _RouteAuthority()
    app = FastAPI()
    config = MiddlewareConfig("trion_session", "x-csrf-token", ("http://localhost:3000",))
    app.add_middleware(SecurityMiddleware, authority=authority, config=config)
    app.include_router(create_security_router(authority, cookie_name="trion_session", cookie_secure=False))

    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"password": TEST_PASSWORD}).status_code == 403
        blocked = client.post(
            "/api/auth/login",
            json={"password": TEST_PASSWORD},
            headers={"origin": "http://attacker.invalid"},
        )
        assert blocked.status_code == 403
        login = client.post(
            "/api/auth/login",
            json={"password": TEST_PASSWORD},
            headers={"origin": "http://localhost:3000"},
        )
        assert login.status_code == 200
        assert client.get("/api/auth/session").status_code == 200
        logout = client.post(
            "/api/auth/logout",
            headers={"origin": "http://localhost:3000", "x-csrf-token": TEST_CSRF},
        )
        assert logout.status_code == 200
        assert client.get("/api/auth/session").status_code == 401
