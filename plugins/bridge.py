from typing import Any
from urllib.parse import unquote, urlsplit

import httpx

from config.infra.security import ADMIN_CSRF_HEADER_NAME
from config.infra.services import ADMIN_API_URL
from mcp.client import call_tool
from mcp.tool_result_contracts import MCPToolResultEnvelope
from plugins.permissions import is_api_allowed, is_tool_allowed

ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
FORWARDED_HEADERS = {"accept", "content-type"}
TRUSTED_HEADERS = {"cookie", "origin", ADMIN_CSRF_HEADER_NAME}
REQUIRED_DELEGATION_HEADERS = TRUSTED_HEADERS


async def proxy_request(
    manifest: dict[str, Any],
    payload: dict[str, Any],
    trusted_headers: dict[str, str],
) -> httpx.Response:
    path = _validate_path(payload.get("path"))
    if not is_api_allowed(manifest, path):
        raise PermissionError(f"Plugin '{manifest['id']}' is not allowed to access '{path}'")
    method = _validate_method(payload.get("method"))
    request_kwargs = _request_kwargs(payload, _verified_headers(trusted_headers))
    async with httpx.AsyncClient(timeout=20.0) as client:
        return await client.request(method, f"{ADMIN_API_URL}{path}", **request_kwargs)


def call_permitted_tool(
    manifest: dict[str, Any],
    tool_name: str,
    args: dict[str, Any],
) -> MCPToolResultEnvelope:
    if not is_tool_allowed(manifest, tool_name):
        raise PermissionError(f"Plugin '{manifest['id']}' is not allowed to call tool '{tool_name}'")
    return call_tool(tool_name, args, timeout=20.0)


def _validate_path(value: Any) -> str:
    path = str(value or "").strip()
    parsed = urlsplit(path)
    if not path or not path.startswith("/") or parsed.scheme or parsed.netloc:
        raise ValueError("Plugin bridge path must be an absolute local path")
    decoded_path = unquote(unquote(parsed.path))
    if (
        parsed.query or parsed.fragment or "\\" in decoded_path or "//" in decoded_path
        or any(segment in {".", ".."} for segment in decoded_path.split("/"))
    ):
        raise ValueError("Plugin bridge path must be canonical")
    return path


def _validate_method(value: Any) -> str:
    method = str(value or "GET").upper().strip()
    if method not in ALLOWED_METHODS:
        raise ValueError(f"Unsupported plugin bridge method '{method}'")
    return method


def _request_kwargs(
    payload: dict[str, Any],
    trusted_headers: dict[str, str],
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"params": payload.get("params") or None}
    headers = _safe_headers(payload.get("headers"))
    headers.update(trusted_headers)
    if headers:
        kwargs["headers"] = headers
    if "json" in payload:
        kwargs["json"] = payload.get("json")
        return kwargs
    if "body" in payload:
        kwargs["content"] = str(payload.get("body") or "").encode("utf-8")
    return kwargs


def _safe_headers(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): str(item)
        for key, item in value.items()
        if str(key).lower() in FORWARDED_HEADERS and str(item).strip()
    }


def _verified_headers(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise PermissionError("Verified plugin delegation headers are required")
    headers = {
        str(key).lower(): str(item)
        for key, item in value.items()
        if str(key).lower() in TRUSTED_HEADERS and str(item).strip()
    }
    if not REQUIRED_DELEGATION_HEADERS.issubset(headers):
        raise PermissionError("Verified plugin delegation headers are required")
    return headers
