"""Global pre-handler authentication, route-scope and CSRF enforcement."""
from __future__ import annotations

from http.cookies import SimpleCookie
import hmac
from typing import Any

from starlette.responses import JSONResponse

from security_contracts import (
    MiddlewareConfig,
    PrincipalKind,
    SECRET_RESOLVE_ROUTE_CONTRACT,
    service_route_allowed,
)
_SAFE_METHODS = frozenset({"GET", "HEAD"})


def _fixed_error(status: int, code: str) -> JSONResponse:
    return JSONResponse({"error": code}, status_code=status, headers={"Cache-Control": "no-store"})


def _resolve_path(path: str) -> bool:
    return SECRET_RESOLVE_ROUTE_CONTRACT.matches_path(path)


def _headers(scope: dict[str, Any]) -> dict[str, str]:
    return {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope.get("headers", ())}


def _cookie(headers: dict[str, str], name: str) -> str:
    try:
        jar = SimpleCookie(headers.get("cookie", ""))
        return jar[name].value if name in jar else ""
    except CookieError:
        return ""


try:
    from http.cookies import CookieError
except ImportError:  # pragma: no cover - supported Python always provides it
    CookieError = ValueError


class SecurityMiddleware:
    def __init__(self, app: Any, *, authority: Any, config: MiddlewareConfig) -> None:
        self.app = app
        self.authority = authority
        self.config = config

    async def _respond(self, scope: dict, receive: Any, send: Any, status: int, code: str) -> None:
        await _fixed_error(status, code)(scope, receive, send)

    def _service_allowed(self, kind: PrincipalKind, method: str, path: str) -> bool:
        return service_route_allowed(kind, method, path)

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        method, path = str(scope.get("method", "")), str(scope.get("path", ""))
        if method == "GET" and path == "/health":
            await self.app(scope, receive, send)
            return
        if method == "POST" and path == "/api/auth/login":
            if not self.authority.is_provisioned():
                await self._respond(scope, receive, send, 503, "AUTH_NOT_PROVISIONED")
                return
            origin = _headers(scope).get("origin", "").rstrip("/")
            if origin not in self.config.allowed_origins:
                await self._respond(scope, receive, send, 403, "AUTH_ORIGIN_REJECTED")
                return
            await self.app(scope, receive, send)
            return
        if not self.authority.is_provisioned():
            await self._respond(scope, receive, send, 503, "AUTH_NOT_PROVISIONED")
            return

        headers = _headers(scope)
        if method == "OPTIONS":
            if headers.get("origin", "").rstrip("/") not in self.config.allowed_origins:
                await self._respond(scope, receive, send, 403, "AUTH_ORIGIN_REJECTED")
                return
            await self.app(scope, receive, send)
            return

        authorization = headers.get("authorization", "")
        if authorization:
            prefix, separator, token = authorization.partition(" ")
            principal = self.authority.authenticate_service(token) if prefix == "Bearer" and separator else None
            if principal is None or not self._service_allowed(principal.kind, method, path):
                await self._respond(scope, receive, send, 403, "AUTH_SERVICE_FORBIDDEN")
                return
            scope.setdefault("state", {})["auth_principal"] = principal
            scope["state"]["auth_token"] = token
            scope["state"]["auth_delegation_headers"] = {}
            await self.app(scope, receive, send)
            return

        session_token = _cookie(headers, self.config.cookie_name)
        principal = self.authority.authenticate_session(session_token) if session_token else None
        if principal is None or (_resolve_path(path) and principal.kind is PrincipalKind.BROWSER):
            await self._respond(scope, receive, send, 401, "AUTH_REQUIRED")
            return

        delegation = {"Cookie": f"{self.config.cookie_name}={session_token}"}
        if method not in _SAFE_METHODS:
            origin = headers.get("origin", "").rstrip("/")
            csrf = headers.get(self.config.csrf_header_name, "")
            if origin not in self.config.allowed_origins:
                await self._respond(scope, receive, send, 403, "AUTH_ORIGIN_REJECTED")
                return
            if not principal.csrf_token or not hmac.compare_digest(csrf, principal.csrf_token):
                await self._respond(scope, receive, send, 403, "AUTH_CSRF_REJECTED")
                return
            delegation.update({"Origin": origin, self.config.csrf_header_name: csrf})
        scope.setdefault("state", {})["auth_principal"] = principal
        scope["state"]["auth_token"] = session_token
        scope["state"]["auth_delegation_headers"] = delegation
        await self.app(scope, receive, send)
