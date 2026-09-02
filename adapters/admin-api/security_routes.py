"""Browser login, session metadata and logout routes."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from security_auth import SecurityAuthority
from security_contracts import PrincipalKind


class LoginRequest(BaseModel):
    password: str


def create_security_router(
    authority: SecurityAuthority,
    *,
    cookie_name: str,
    cookie_secure: bool,
) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/login")
    async def login(body: LoginRequest) -> JSONResponse:
        if not authority.is_provisioned():
            return JSONResponse({"error": "AUTH_NOT_PROVISIONED"}, status_code=503)
        if not authority.verify_password(body.password):
            return JSONResponse({"error": "AUTH_INVALID_CREDENTIAL"}, status_code=401)
        issued = authority.issue_session()
        response = JSONResponse({"principal": "admin", "expires_at": issued.expires_at, "csrf_token": issued.csrf_token})
        response.set_cookie(
            cookie_name,
            issued.token,
            max_age=authority.ttl_seconds,
            httponly=True,
            secure=cookie_secure,
            samesite="strict",
            path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @router.get("/session")
    async def session(request: Request) -> JSONResponse:
        principal = getattr(request.state, "auth_principal", None)
        if principal is None or principal.kind is not PrincipalKind.BROWSER:
            return JSONResponse({"error": "AUTH_REQUIRED"}, status_code=401)
        return JSONResponse(
            {
                "principal": principal.subject,
                "expires_at": principal.expires_at,
                "csrf_token": principal.csrf_token,
            },
            headers={"Cache-Control": "no-store"},
        )

    @router.post("/logout")
    async def logout() -> JSONResponse:
        authority.revoke_sessions()
        response = JSONResponse({"status": "logged_out"}, headers={"Cache-Control": "no-store"})
        response.delete_cookie(cookie_name, path="/", secure=cookie_secure, httponly=True, samesite="strict")
        return response

    return router
