#!/usr/bin/env python3
"""Generate docs/reference/20-backend-api-reference.md from FastAPI route decorators.

Walks adapters/admin-api/, extracts @router.METHOD("path") decorators per file,
honours APIRouter(prefix=...) declarations and produces a Markdown reference.

Run from repo root:
    .venv/bin/python scripts/dump_endpoints.py > docs/reference/20-backend-api-reference.md
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN_API = ROOT / "adapters" / "admin-api"

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}
API_REFERENCE_UPDATED = "2026-09-01"


def _imported_string_constants(tree: ast.Module) -> dict[str, str]:
    """Resolve direct string constants imported from repository modules."""
    values: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        source = ROOT / f"{node.module.replace('.', '/')}.py"
        if not source.is_file():
            continue
        imported = ast.parse(source.read_text(encoding="utf-8"))
        literals = {
            item.targets[0].id: str(item.value.value)
            for item in imported.body
            if isinstance(item, ast.Assign)
            and len(item.targets) == 1
            and isinstance(item.targets[0], ast.Name)
            and isinstance(item.value, ast.Constant)
            and isinstance(item.value.value, str)
        }
        for alias in node.names:
            if alias.name in literals:
                values[alias.asname or alias.name] = literals[alias.name]
    return values


def _resolve_string(node: ast.AST, values: dict[str, str], prefix: str) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return values.get(node.id)
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "router"
        and node.attr == "prefix"
    ):
        return prefix
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        base = _resolve_string(node.func.value, values, prefix)
        arg = _resolve_string(node.args[0], values, prefix) if len(node.args) == 1 else None
        if base is not None and arg is not None and node.func.attr == "removeprefix":
            return base.removeprefix(arg)
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for item in node.values:
            target = item.value if isinstance(item, ast.FormattedValue) else item
            value = _resolve_string(target, values, prefix)
            if value is None:
                return None
            parts.append(value)
        return "".join(parts)
    return None


def extract_router_prefix(tree: ast.Module) -> str:
    """Find APIRouter(prefix='...') in module body and return prefix."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            value = node.value
            if isinstance(value, ast.Call) and getattr(value.func, "id", None) == "APIRouter":
                for keyword in value.keywords:
                    if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant):
                        return str(keyword.value.value)
    return ""


def extract_routes(tree: ast.Module, prefix: str) -> list[tuple[str, str, str, str]]:
    """Return [(method, path, function_name, docstring_first_line), ...]."""
    routes: list[tuple[str, str, str, str]] = []
    values = _imported_string_constants(tree)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not isinstance(func, ast.Attribute):
                continue
            if not isinstance(func.value, ast.Name):
                continue
            if func.value.id not in {"router", "app"}:
                continue
            if func.attr.lower() not in HTTP_METHODS:
                continue
            path_node = decorator.args[0] if decorator.args else next(
                (keyword.value for keyword in decorator.keywords if keyword.arg == "path"), None
            )
            if path_node is None:
                raise ValueError(f"unresolved route path for {node.name}: missing path")
            path = _resolve_string(path_node, values, prefix)
            if path is None:
                expression = ast.unparse(path_node)
                raise ValueError(f"unresolved route path for {node.name}: {expression}")
            doc = ast.get_docstring(node) or ""
            doc_first = doc.split("\n", 1)[0].strip().replace("|", "\\|")
            routes.append((func.attr.upper(), path, node.name, doc_first))
    return routes


def parse_file(path: Path) -> tuple[str, list[tuple[str, str, str, str]]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    prefix = extract_router_prefix(tree)
    return prefix, extract_routes(tree, prefix)


def collect_files() -> list[Path]:
    return [p for p in sorted(ADMIN_API.rglob("*.py")) if "__pycache__" not in p.parts]


def render() -> str:
    out: list[str] = [
        "---",
        "title: Backend-API-Reference",
        "tags: [backend, api, reference, admin-api]",
        "created: 2026-06-15",
        f"updated: {API_REFERENCE_UPDATED}",
        "status: ACTIVE",
        "authority: backend-api-reference",
        "---",
        "",
        "# Backend-API-Reference",
        "",
        "[Back to README](../../README.md)",
        "",
        "Vollständige, mechanisch generierte Liste aller HTTP-Endpunkte unter",
        "`adapters/admin-api/`. **Diese Doku wird automatisch erzeugt** —",
        "regeneriere sie mit `.venv/bin/python scripts/dump_endpoints.py > docs/reference/20-backend-api-reference.md`",
        "(Quelle: `scripts/dump_endpoints.py`).",
        "",
        "This generated inventory includes both WebUI-facing and internal endpoints.",
        "It describes the code surface; it does not imply that the development stack is",
        "safe to expose to an untrusted network.",
        "",
        "## Hinweise",
        "",
        "- Effektiver Pfad = `APIRouter(prefix=...)` + Decorator-Pfad.",
        "- `commander_api/*`-Sub-Router werden in `commander_routes.py` ohne Prefix eingehängt — die Pfade gelten so wie im Decorator.",
        "- `trion_memory_router` ist zusätzlich unter `/trion/memory/...` gemountet (Sonderfall, hier nicht doppelt gelistet).",
        "- Diese Liste ist das lokale Decorator-Inventar unter `adapters/admin-api`; sie erhebt keinen Anspruch auf alle gemounteten Backend-Endpunkte.",
        "- Importierte Router-Mounts werden durch `adapters/admin-api/main.py` und die kuratierten Endpointdokumente beschrieben.",
        "",
    ]

    total = 0
    for path in collect_files():
        prefix, routes = parse_file(path)
        if not routes:
            continue
        rel = path.relative_to(ROOT)
        out.append(f"## `{rel}`")
        if prefix:
            out.append(f"_Prefix:_ `{prefix}`")
        out.append("")
        out.append("| Methode | Pfad | Handler | Beschreibung |")
        out.append("|---------|------|---------|--------------|")
        for method, route_path, func_name, doc in sorted(routes, key=lambda r: (r[1], r[0])):
            full = f"{prefix}{route_path}" if prefix else route_path
            description = doc or "—"
            out.append(f"| `{method}` | `{full}` | `{func_name}()` | {description} |")
            total += 1
        out.append("")

    out.extend([
        "---",
        "",
        f"**Gesamt:** {total} Endpunkte.",
        "",
    ])
    return "\n".join(out)


if __name__ == "__main__":
    print(render(), end="")
