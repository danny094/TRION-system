"""Static P16-SP1 contracts for the two internal Admin API callers."""

from __future__ import annotations

import ast
from pathlib import Path

from config.infra.security import (
    SECRET_RESOLVE_ROUTE_PREFIX,
    get_memory_read_token_path,
    get_secret_resolve_token_path,
)
from memory.embedding.config import MEMORY_READ_ROUTES

ROOT = Path(__file__).resolve().parents[1]
CORE_SECRETS = ROOT / "core/llm/secrets.py"
SECURITY_CONTRACTS = ROOT / "adapters" / "admin-api" / "security_contracts.py"
SECURITY_MIDDLEWARE = ROOT / "adapters" / "admin-api" / "security_middleware.py"
SECRETS_ROUTES = ROOT / "adapters" / "admin-api" / "secrets_routes.py"
SETTINGS_ROUTES = ROOT / "adapters" / "admin-api" / "settings_routes.py"
RUNTIME_ROUTES = ROOT / "adapters" / "admin-api" / "runtime_routes.py"
SKILL_SECRETS = ROOT / "config/skills/secrets.py"
MEMORY_CONFIG = ROOT / "memory/embedding/config.py"
ADMIN_ENTRYPOINT = ROOT / "adapters/admin-api/docker-entrypoint.sh"
MEMORY_FILES = (
    ROOT / "memory/embedding/config.py",
    ROOT / "memory/embedding/model_resolver.py",
    ROOT / "memory/embedding/runtime_config.py",
)

def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _string_literals(source: str) -> set[str]:
    return {
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _requests_calls(source: str) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if isinstance(node.func.value, ast.Name) and node.func.value.id == "requests":
            calls.append(node)
    return calls


def _route_decorators(source: str) -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "router":
            continue
        if node.func.attr not in {"get", "post"}:
            continue
        routes.add((node.func.attr, ast.unparse(node.args[0])))
    return routes


def _token_env_reads(source: str) -> list[str]:
    reads: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not (
            isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
            and node.func.attr == "getenv"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            continue
        name = str(node.args[0].value)
        if "TOKEN" in name.upper():
            reads.append(name)
    return reads


def _endpoint_env_reads(source: str) -> list[str]:
    names = ("SECRETS_API_URL", "ADMIN_API_URL", "TRION_ADMIN_API_URL", "SETTINGS_API_URL")
    return [name for name in names if f'getenv("{name}"' in source]


def test_secret_resolver_token_comes_only_from_its_secret_file() -> None:
    source = _source(CORE_SECRETS)

    assert "SECRET_RESOLVE_TOKEN_FILE" in source
    assert ".read_text(" in source
    assert "INTERNAL_SECRET_RESOLVE_TOKEN" not in source
    assert '".env"' not in source and "'.env'" not in source
    assert _token_env_reads(source) == []
    assert _endpoint_env_reads(source) == []
    assert "SECRET_RESOLVE_ROUTE_PREFIX" in source
    assert "MEMORY_READ_TOKEN" not in source


def test_internal_token_paths_have_one_config_authority() -> None:
    skill_source = _source(SKILL_SECRETS)
    memory_source = _source(MEMORY_CONFIG)
    entrypoint_source = _source(ADMIN_ENTRYPOINT)

    assert "get_secret_resolve_token_path" in skill_source
    assert str(get_secret_resolve_token_path()) not in skill_source
    assert "TRION_SECRET_RESOLVE_TOKEN_FILE" not in skill_source
    assert "get_memory_read_token_path" in memory_source
    assert str(get_memory_read_token_path()) not in memory_source
    assert "TRION_MEMORY_READ_TOKEN_FILE" not in memory_source
    assert "/run/trion-security/" not in entrypoint_source
    for name in ("TRION_SECRET_RESOLVE_TOKEN_FILE", "TRION_MEMORY_READ_TOKEN_FILE"):
        assert f': "${{{name}:?' in entrypoint_source


def test_secret_resolver_uses_bearer_on_get_only() -> None:
    source = _source(CORE_SECRETS)

    assert "SECRET_RESOLVE_ROUTE_PREFIX" in source
    assert '"Authorization"' in source and "Bearer " in source
    assert source.count("await client.get(") == 1
    for method in ("post", "put", "patch", "delete"):
        assert f"await client.{method}(" not in source


def test_memory_caller_uses_only_the_memory_read_secret_file() -> None:
    source = "\n".join(_source(path) for path in MEMORY_FILES)

    assert "MEMORY_READ_TOKEN_FILE" in source
    assert ".read_text(" in source
    assert _token_env_reads(source) == []
    assert set(_endpoint_env_reads(source)) == {"ADMIN_API_URL", "SETTINGS_API_URL"}
    assert "_ALLOWED_ADMIN_API_URLS" in source
    assert "candidate not in _ALLOWED_ADMIN_API_URLS" in source
    assert "http://trion-admin-api:8200" in source
    assert "http://127.0.0.1:8200" in source
    assert "http://localhost:8200" in source
    assert "SECRET_RESOLVE_TOKEN" not in source
    assert "INTERNAL_SECRET_RESOLVE_TOKEN" not in source


def test_memory_bearer_is_limited_to_three_exact_get_routes() -> None:
    sources = [_source(path) for path in MEMORY_FILES]
    combined = "\n".join(sources)
    literals = set().union(*(_string_literals(source) for source in sources))
    calls = [call for source in sources for call in _requests_calls(source)]

    assert MEMORY_READ_ROUTES <= literals
    assert '"Authorization"' in combined and "Bearer " in combined
    assert len(calls) == 3
    assert all(call.func.attr == "get" for call in calls)
    assert all(any(keyword.arg == "headers" for keyword in call.keywords) for call in calls)
    expected_calls = {
        "model_resolver.py": "MODELS_EFFECTIVE_ROUTE",
        "runtime_config.py": "EMBEDDINGS_RUNTIME_ROUTE",
    }
    for path in MEMORY_FILES:
        source = _source(path)
        route_name = expected_calls.get(path.name)
        if route_name:
            assert f'f"{{ADMIN_API_URL}}{{{route_name}}}"' in source
    assert 'f"{base}{COMPUTE_ROUTING_ROUTE}"' in _source(MEMORY_FILES[2])


def test_admin_handlers_consume_the_canonical_internal_route_authorities() -> None:
    secret_routes = _route_decorators(_source(SECRETS_ROUTES))
    settings_routes = _route_decorators(_source(SETTINGS_ROUTES))
    runtime_routes = _route_decorators(_source(RUNTIME_ROUTES))

    relative = "SECRET_RESOLVE_ROUTE_PREFIX.removeprefix(router.prefix)"
    assert ("get", f"f'{{{relative}}}/{{{{name}}}}'") in secret_routes
    assert ("get", "MODELS_EFFECTIVE_ROUTE.removeprefix(router.prefix)") in settings_routes
    assert ("get", "EMBEDDINGS_RUNTIME_ROUTE.removeprefix(router.prefix)") in settings_routes
    assert ("post", "EMBEDDINGS_RUNTIME_ROUTE.removeprefix(router.prefix)") in settings_routes
    assert ("get", "COMPUTE_ROUTING_ROUTE") in runtime_routes
    assert ("post", "COMPUTE_ROUTING_ROUTE") in runtime_routes


def test_middleware_consumes_the_shared_service_route_authority() -> None:
    contracts = _source(SECURITY_CONTRACTS)
    middleware = _source(SECURITY_MIDDLEWARE)

    assert "MEMORY_READ_ROUTES" in contracts
    assert "SECRET_RESOLVE_ROUTE_PREFIX" in contracts
    assert "service_route_allowed" in middleware
    assert all(route not in middleware for route in MEMORY_READ_ROUTES)
    assert SECRET_RESOLVE_ROUTE_PREFIX not in middleware


def test_internal_tokens_do_not_cross_owner_boundaries() -> None:
    core_source = _source(CORE_SECRETS)
    memory_source = "\n".join(_source(path) for path in MEMORY_FILES)

    assert "MEMORY_READ_TOKEN" not in core_source
    assert "SECRET_RESOLVE_TOKEN" not in memory_source
