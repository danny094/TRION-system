import ast
import re
from pathlib import Path
import pytest
from scripts.dump_endpoints import extract_routes, render as render_api_reference
ROOT = Path(__file__).resolve().parents[1]
WEBUI = ROOT / "adapters" / "webui" / "src"
APP = WEBUI / "App.tsx"
CLIENT = WEBUI / "lib" / "api" / "client.ts"
CHAT_API = WEBUI / "features" / "chat" / "api.ts"
MEMORY_API = WEBUI / "features" / "memory" / "api.ts"
PLUGIN_HOST = WEBUI / "lib" / "contracts" / "pluginHost.ts"
PLUGIN_FRAME = WEBUI / "features" / "plugins" / "components" / "PluginFrame.tsx"
AUTH = WEBUI / "features" / "auth"
EN = WEBUI / "lib" / "i18n" / "enExtra.ts"
DE = WEBUI / "lib" / "i18n" / "deExtra.ts"
API_REFERENCE = ROOT / "docs" / "reference" / "20-backend-api-reference.md"
API_GENERATOR = ROOT / "scripts" / "dump_endpoints.py"
ADMIN_MAIN = ROOT / "adapters" / "admin-api" / "main.py"
MCP_ENDPOINT = ROOT / "mcp" / "endpoint.py"
def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")
def test_auth_gate_wraps_the_desktop_shell() -> None:
    source = _read(APP)

    assert "features/auth/AuthGate" in source
    assert re.search(
        r"<AuthGate(?:\s[^>]*)?>\s*<DesktopShell\s*/>\s*</AuthGate>",
        source,
    )

def test_auth_feature_contract_and_styles_are_materialized() -> None:
    contracts = AUTH / "contracts.ts"
    gate = AUTH / "AuthGate.tsx"
    styles = AUTH / "AuthGate.css"

    assert contracts.is_file()
    assert gate.is_file()
    assert styles.is_file()
    contract_source = _read(contracts).lower()
    gate_source = _read(gate)
    assert all(field in contract_source for field in ("principal", "expires", "csrf"))
    assert set(re.findall(r"status:\s*'([^']+)'", contract_source)) == {
        "checking", "anonymous", "authenticated",
    }
    assert "AuthGate.css" in gate_source
    assert "@/lib/api/client" in gate_source
    assert "setCsrfToken(session.csrf_token)" in gate_source
    assert gate_source.count("setCsrfToken(null)") >= 2
    assert gate_source.count("{children}") == 1
    children = gate_source.index("{children}")
    assert gate_source.index("if (state.status === 'checking')") < children
    assert gate_source.index("if (state.status === 'anonymous')") < children

def test_central_client_owns_credentials_csrf_and_session_loss() -> None:
    source = _read(CLIENT)
    gate = _read(AUTH / "AuthGate.tsx")
    lowered = source.lower()

    assert re.search(r"credentials\s*:\s*['\"]same-origin['\"]", source)
    assert "csrf" in lowered
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        assert re.search(rf"['\"]{method}['\"]", source)
    assert re.search(
        r"MUTATING_METHODS\.has\(method\)\s*&&\s*csrfToken[\s\S]{0,160}"
        r"headers\.set\(['\"]x-csrf-token['\"],\s*csrfToken\)",
        source,
    )
    assert re.search(
        r"401[\s\S]{0,500}(dispatchEvent|CustomEvent)",
        source,
    )
    assert "export const SESSION_LOST_EVENT" in source
    assert "SESSION_LOST_EVENT" in gate.split("from '@/lib/api/client'", 1)[0]
    assert "const SESSION_LOST_EVENT" not in gate

def test_failed_logout_preserves_the_authenticated_session() -> None:
    source = _read(AUTH / "AuthGate.tsx")
    logout = source.split("async function logout()", 1)[1].split("if (state.status === 'checking')", 1)[0]

    assert "catch" in logout
    assert "auth.logoutFailed" in logout
    assert "finally" not in logout
    assert logout.index("await fetchApiResponse") < logout.index("setCsrfToken(null)")

def test_api_consumers_use_the_central_security_client() -> None:
    for path in (CHAT_API, MEMORY_API, PLUGIN_HOST):
        source = _read(path)
        assert "@/lib/api/client" in source, path
        assert re.search(r"\bfetch\s*\(", source) is None, path


def test_chat_keeps_the_ndjson_response_path() -> None:
    source = _read(CHAT_API)

    assert "parseNDJSONStream" in source
    assert re.search(r"parseNDJSONStream\(response\)", source)


def test_both_catalogs_contain_login_copy() -> None:
    for path, password_word in ((EN, "password"), (DE, "passwort")):
        auth_lines = [line.lower() for line in _read(path).splitlines() if "'auth." in line]
        copy = " ".join(auth_lines)
        assert auth_lines, path
        assert "auth.logoutfailed" in copy, path
        assert password_word in copy, path
        assert any(word in copy for word in ("login", "sign in", "anmelden")), path
        assert "session" in copy or "sitzung" in copy, path

def test_generated_api_reference_has_governed_frontmatter() -> None:
    rendered = render_api_reference()
    frontmatter = rendered.split("---", 2)[1]
    generator_source = _read(API_GENERATOR)

    assert "created: 2026-06-15" in frontmatter
    assert "updated: 2026-09-01" in frontmatter
    assert "status: ACTIVE" in frontmatter
    assert "authority: backend-api-reference" in frontmatter
    assert "date.today" not in generator_source
    assert _read(API_REFERENCE) == rendered


@pytest.mark.parametrize("decorator", ["@router.get(UNKNOWN_PATH)", "@router.get(path=UNKNOWN_PATH)"])
def test_endpoint_generator_rejects_an_unresolved_http_route(decorator: str) -> None:
    tree = ast.parse(f"{decorator}\ndef unresolved():\n    pass\n")

    with pytest.raises(ValueError, match="unresolved.*UNKNOWN_PATH"):
        extract_routes(tree, "")


def test_generated_routes_match_the_product_router_authority() -> None:
    generated = _read(API_REFERENCE)

    for route in ("`/api/protocol/list`", "`/blueprints`", "`/unlock`"):
        assert route in generated
    assert "lokale Decorator-Inventar unter `adapters/admin-api`" in generated
    assert "*alle* Backend-Endpunkte" not in generated
    assert "`trion_memory_router`" in generated
    assert "`/trion/memory/...`" in generated
    assert 'include_router(mcp_installer_router, prefix="/api/mcp")' in _read(ADMIN_MAIN)
    assert '@router.post("/mcp")' in _read(MCP_ENDPOINT)


def test_plugin_host_uses_only_an_opaque_origin_iframe() -> None:
    host, frame = _read(PLUGIN_HOST), _read(PLUGIN_FRAME)
    assert "return entry.endsWith('.html') ? 'iframe' : 'blocked'" in host
    assert all(token not in frame for token in ("PluginHostMount", "usePluginModule", "import("))
    sandbox = re.search(r'sandbox="([^"]+)"', frame)
    assert sandbox and "allow-scripts" in sandbox.group(1)
    assert "allow-same-origin" not in sandbox.group(1)
