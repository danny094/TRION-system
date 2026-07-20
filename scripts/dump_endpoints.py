#!/usr/bin/env python3
"""Generate docs/reference/20-backend-api-reference.md from FastAPI route decorators.

Walks adapters/admin-api/, extracts @router.METHOD("path") decorators per file,
honours APIRouter(prefix=...) declarations and produces a Markdown reference.

Run from repo root:
    .venv/bin/python scripts/dump_endpoints.py > docs/reference/20-backend-api-reference.md
"""
from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN_API = ROOT / "adapters" / "admin-api"

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}


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


def extract_routes(tree: ast.Module) -> list[tuple[str, str, str, str]]:
    """Return [(method, path, function_name, docstring_first_line), ...]."""
    routes: list[tuple[str, str, str, str]] = []
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
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            path = str(decorator.args[0].value)
            doc = ast.get_docstring(node) or ""
            doc_first = doc.split("\n", 1)[0].strip().replace("|", "\\|")
            routes.append((func.attr.upper(), path, node.name, doc_first))
    return routes


def parse_file(path: Path) -> tuple[str, list[tuple[str, str, str, str]]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return extract_router_prefix(tree), extract_routes(tree)


def collect_files() -> list[Path]:
    return [p for p in sorted(ADMIN_API.rglob("*.py")) if "__pycache__" not in p.parts]


def render() -> str:
    today = date.today().isoformat()
    out: list[str] = [
        "---",
        "title: Backend-API-Reference",
        "tags: [backend, api, reference, admin-api]",
        f"updated: {today}",
        "---",
        "",
        "# Backend-API-Reference",
        "",
        "← [[TRION|Zurück zur Übersicht]]",
        "",
        "Vollständige, mechanisch generierte Liste aller HTTP-Endpunkte unter",
        "`adapters/admin-api/`. **Diese Doku wird automatisch erzeugt** —",
        "regeneriere sie mit `.venv/bin/python scripts/dump_endpoints.py > docs/reference/20-backend-api-reference.md`",
        "(Quelle: `scripts/dump_endpoints.py`).",
        "",
        "Für die kuratierte Sicht auf nur die WebUI-relevanten Endpunkte siehe",
        "[[17-webui-api-endpoints|WebUI-API-Endpunkte]].",
        "",
        "## Hinweise",
        "",
        "- Effektiver Pfad = `APIRouter(prefix=...)` + Decorator-Pfad.",
        "- `commander_api/*`-Sub-Router werden in `commander_routes.py` ohne Prefix eingehängt — die Pfade gelten so wie im Decorator.",
        "- `trion_memory_router` ist zusätzlich unter `/trion/memory/...` gemountet (Sonderfall, hier nicht doppelt gelistet).",
        "- Diese Liste enthält *alle* Backend-Endpunkte, auch interne (z. B. `/api/secrets/resolve/{name}`, Bearer-geschützt) und Übergangspfade (`/api/storage-broker/*`).",
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
