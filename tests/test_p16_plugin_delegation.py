import ast, asyncio, re, sys
from pathlib import Path
import pytest
from fastapi import HTTPException, Request
from config.infra.security import ADMIN_CSRF_HEADER_NAME
from plugins import bridge as plugin_bridge
from plugins.bridge import TRUSTED_HEADERS, _request_kwargs, _verified_headers

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters" / "admin-api"))
import plugins_routes  # noqa: E402
ROUTES = ROOT / "adapters" / "admin-api" / "plugins_routes.py"
BRIDGE = ROOT / "plugins" / "bridge.py"
RUNTIME_BRIDGE = ROOT / "plugins" / "runtime_bridge.js"
PROTECTED_HEADERS = {"authorization", "cookie", "origin", ADMIN_CSRF_HEADER_NAME}
REQUIRED_DELEGATION_HEADERS = {"cookie", "origin", ADMIN_CSRF_HEADER_NAME}
def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
def _function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"missing function: {name}")
def _calls(node: ast.AST, name: str) -> list[ast.Call]:
    return [
        item for item in ast.walk(node) if isinstance(item, ast.Call)
        and ((isinstance(item.func, ast.Name) and item.func.id == name) or
             (isinstance(item.func, ast.Attribute) and item.func.attr == name))
    ]

def _is_delegation_state_access(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute) and node.attr == "auth_delegation_headers"
        and isinstance(node.value, ast.Attribute) and node.value.attr == "state"
        and isinstance(node.value.value, ast.Name) and node.value.value.id == "request"
    )

def test_plugin_route_delegates_only_server_verified_request_state() -> None:
    function = _function(_tree(ROUTES), "bridge_plugin_request")
    parameters = {argument.arg for argument in function.args.args}
    assert "request" in parameters

    state_names: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if value is not None and _is_delegation_state_access(value):
                state_names.update(
                    target.id for target in targets if isinstance(target, ast.Name)
                )
    calls = _calls(function, "proxy_request")
    assert len(calls) == 1
    call = calls[0]
    assert len(call.args) == 3
    trusted = call.args[2]
    assert _is_delegation_state_access(trusted) or (
        isinstance(trusted, ast.Name) and trusted.id in state_names
    )
    assert isinstance(call.args[1], ast.Name) and call.args[1].id == "payload"

def test_bridge_accepts_trusted_headers_separately_from_payload() -> None:
    tree = _tree(BRIDGE)
    proxy = _function(tree, "proxy_request")
    parameters = [argument.arg for argument in proxy.args.args]
    assert len(parameters) >= 3
    trusted_name = parameters[2]
    assert "trusted" in trusted_name or "delegation" in trusted_name

    request_kwargs_calls = _calls(proxy, "_request_kwargs")
    assert len(request_kwargs_calls) == 1
    verified_calls = _calls(proxy, "_verified_headers")
    assert len(verified_calls) == 1
    assert verified_calls[0] in ast.walk(request_kwargs_calls[0])
    assert any(
        isinstance(item, ast.Name) and item.id == trusted_name
        for item in ast.walk(request_kwargs_calls[0])
    )

    assignments = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "FORWARDED_HEADERS"
    }
    assert assignments["FORWARDED_HEADERS"] == {"accept", "content-type"}
    assert assignments["FORWARDED_HEADERS"].isdisjoint(PROTECTED_HEADERS)

    kwargs_function = _function(tree, "_request_kwargs")
    kwargs_parameters = {argument.arg for argument in kwargs_function.args.args}
    assert trusted_name in kwargs_parameters
    payload_header_reads = [
        call
        for call in _calls(kwargs_function, "get")
        if isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "payload"
        and call.args
        and isinstance(call.args[0], ast.Constant)
        and call.args[0].value == "headers"
    ]
    assert len(payload_header_reads) == 1
    safe_header_calls = _calls(kwargs_function, "_safe_headers")
    assert len(safe_header_calls) == 1
    assert any(read in ast.walk(safe_header_calls[0]) for read in payload_header_reads)
    trusted_updates = [
        call
        for call in _calls(kwargs_function, "update")
        if any(
            isinstance(item, ast.Name) and item.id == trusted_name
            for item in ast.walk(call)
        )
    ]
    assert len(trusted_updates) == 1
    assert payload_header_reads[0].lineno < trusted_updates[0].lineno

    assert TRUSTED_HEADERS == {"cookie", "origin", ADMIN_CSRF_HEADER_NAME}


def test_runtime_bridge_and_assets_keep_the_browser_boundary(monkeypatch, tmp_path: Path) -> None:
    source = RUNTIME_BRIDGE.read_text(encoding="utf-8")
    lowered = source.lower()
    response = asyncio.run(plugins_routes.get_plugin_bridge_script())
    served = response.body.decode("utf-8")
    assert "__TRION_CSRF_HEADER_NAME__" in source
    assert ADMIN_CSRF_HEADER_NAME not in source
    assert "__TRION_CSRF_HEADER_NAME__" not in served
    assert ADMIN_CSRF_HEADER_NAME in served
    assert "/api/auth/session" in source
    assert "csrf" in lowered
    assert "credentials" in lowered and "same-origin" in lowered
    assert re.search(r"csrfToken\s*=\s*String\(session\.csrf_token", source)
    assert re.search(r"const\s+csrf\s*=\s*await\s+sessionCsrf\(\)", source)
    assert re.search(r"\[csrfHeaderName\]\s*:\s*csrf\b", source)
    for forbidden in ("authorization", "bearer", "service_secret", "internal_secret", "memory_read_token"):
        assert forbidden not in lowered
    monkeypatch.setattr(plugins_routes, "plugin_exists", lambda _plugin_id: True)
    for asset_name in ("index.html", "entry.js", "entry.mjs"):
        asset = tmp_path / asset_name
        asset.write_text("void 0", encoding="utf-8")
        monkeypatch.setattr(plugins_routes, "resolve_plugin_asset", lambda *_args, target=asset: target)
        response = asyncio.run(plugins_routes.get_plugin_asset("test", asset_name))
        csp = response.headers["content-security-policy"]
        assert "sandbox" in csp and "allow-same-origin" not in csp
        assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize("missing", sorted(REQUIRED_DELEGATION_HEADERS))
def test_incomplete_browser_delegation_is_rejected(missing: str) -> None:
    trusted = {
        "cookie": "trion_session=TEST-ONLY",
        "origin": "http://localhost:3000",
        "x-csrf-token": "TEST-ONLY-csrf",
    }
    trusted.pop(missing)
    with pytest.raises(PermissionError, match="Verified plugin delegation headers"):
        _verified_headers(trusted)


def test_hostile_payload_headers_cannot_override_verified_browser_delegation() -> None:
    trusted = {
        "Cookie": "trion_session=TEST-ONLY-trusted",
        "Origin": "http://localhost:3000",
        "x-csrf-token": "TEST-ONLY-trusted-csrf",
    }
    payload = {
        "headers": {
            "Accept": "application/json",
            "Authorization": "Bearer TEST-ONLY-hostile",
            "Cookie": "trion_session=TEST-ONLY-hostile",
            "Origin": "http://attacker.invalid",
            "x-csrf-token": "TEST-ONLY-hostile-csrf",
        }
    }

    headers = _request_kwargs(payload, _verified_headers(trusted))["headers"]
    lowered = {key.lower(): value for key, value in headers.items()}
    assert lowered["accept"] == "application/json"
    assert lowered["cookie"] == trusted["Cookie"]
    assert lowered["origin"] == trusted["Origin"]
    assert lowered["x-csrf-token"] == trusted["x-csrf-token"]
    assert "authorization" not in lowered


def test_hostile_payload_and_noncanonical_paths_fail_before_permissions(monkeypatch) -> None:
    monkeypatch.setattr(plugins_routes, "_require_plugin_manifest", lambda _plugin_id: {})
    hostile = {"headers": {name: "TEST-ONLY-hostile" for name in PROTECTED_HEADERS}}
    for state in ({}, {"auth_delegation_headers": "TEST-ONLY-invalid"}):
        request = Request({"type": "http", "state": state})
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(plugins_routes.bridge_plugin_request("test", request, hostile))
        assert exc_info.value.status_code == 403
    permission_checks: list[str] = []
    monkeypatch.setattr(plugin_bridge, "is_api_allowed", lambda _manifest, path: permission_checks.append(path))
    for hostile_path in ("/api/../admin", "/api/./allowed", "/api/%2e%2e/admin", "/api/%252e%252e/admin"):
        with pytest.raises(ValueError, match="canonical"):
            asyncio.run(plugin_bridge.proxy_request({"id": "test"}, {"path": hostile_path}, {}))
    assert permission_checks == []
