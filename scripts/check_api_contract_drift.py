#!/usr/bin/env python3
"""Report static Admin API routes that are absent from the generated API reference."""
from __future__ import annotations
import ast
from pathlib import Path

METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}

def router_prefix(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "APIRouter":
            for keyword in node.value.keywords:
                if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant): return str(keyword.value.value)
    return ""

def routes(root):
    values = set()
    for path in (root / "adapters/admin-api").rglob("*.py"):
        if "__pycache__" in path.parts: continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        prefix = router_prefix(tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): continue
            for decorator in node.decorator_list:
                func = getattr(decorator, "func", None)
                if isinstance(func, ast.Attribute) and func.attr in METHODS and getattr(decorator, "args", None):
                    first = decorator.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str): values.add(f"{prefix}{first.value}")
    return values

def main():
    root = Path(__file__).resolve().parents[1]; reference = (root / "docs/reference/20-backend-api-reference.md").read_text(encoding="utf-8", errors="replace")
    rows = [f"api_route {route} absent from reference" for route in sorted(routes(root)) if route and f"`{route}`" not in reference]
    print("API-contract drift check: REVIEW_REQUIRED candidates:" if rows else "API-contract drift check: no static route candidates.")
    if rows: print("\n".join(f"  {row}" for row in rows))
    return 0

if __name__ == "__main__": raise SystemExit(main())
