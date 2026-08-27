#!/usr/bin/env python3
"""Check Doc07 Python import directions for changed files only.

The result is structural evidence, not an architecture-audit decision.
Relative imports are resolved to their project root before evaluating Doc07.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

# Project roots relevant to Doc07 boundary checks. Isolated roots must not
# silently bypass the rule by importing a root outside the arrow diagram.
PROJECT_ROOTS = frozenset(
    {
        "adapters",
        "config",
        "core",
        "intelligence_modules",
        "mcp",
        "mcp-servers",
        "memory",
        "personas",
        "plugins",
        "tools",
        "utils",
    }
)

# Doc07's explicit import roots and their allowed direct project-root imports.
IMPORT_RULES = {
    "utils": {"utils"},
    "config": {"config"},
    "core": {"core", "utils", "config"},
    "mcp": {"mcp", "utils"},
    "tools": {"tools", "mcp", "utils"},
    "adapters": PROJECT_ROOTS,
    "mcp-servers": PROJECT_ROOTS - {"adapters", "core", "mcp"},
}
LOADER_MODULE = re.compile(r"^intelligence_modules\.cim_skill_rag\.[A-Za-z_]\w*_loader$")


def git_paths(args: list[str], root: Path) -> set[Path]:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return {Path(line) for line in result.stdout.splitlines() if line.strip()}


def changed_python_paths(root: Path) -> list[Path]:
    paths = git_paths(["diff", "--name-only"], root)
    paths |= git_paths(["diff", "--cached", "--name-only"], root)
    paths |= git_paths(["ls-files", "--others", "--exclude-standard"], root)
    return sorted(path for path in paths if path.suffix == ".py" and (root / path).is_file())


def imported_nodes(tree: ast.Module, path: Path) -> list[tuple[int, str, ast.Import | ast.ImportFrom]]:
    imports: list[tuple[int, str, ast.Import | ast.ImportFrom]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((node.lineno, alias.name.split(".", 1)[0], node) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported = _imported_root(node, path)
            if imported:
                imports.append((node.lineno, imported, node))
    return imports


def _imported_root(node: ast.ImportFrom, path: Path) -> str | None:
    if node.level == 0:
        return node.module.split(".", 1)[0] if node.module else None
    package_parts = list(path.with_suffix("").parts[:-1])
    parent_count = node.level - 1
    if parent_count > len(package_parts):
        return "<outside-project>"
    base = package_parts[: len(package_parts) - parent_count] if parent_count else package_parts
    module_parts = node.module.split(".") if node.module else []
    target_parts = base + module_parts
    return target_parts[0] if target_parts else None


def is_absolute_loader_import(node: ast.Import | ast.ImportFrom) -> bool:
    if isinstance(node, ast.Import):
        return all(LOADER_MODULE.fullmatch(alias.name) for alias in node.names)
    if node.level:
        return False
    if node.module and LOADER_MODULE.fullmatch(node.module):
        return True
    return node.module == "intelligence_modules.cim_skill_rag" and all(
        alias.name.endswith("_loader") for alias in node.names
    )


def violations_for(path: Path, root: Path) -> list[str]:
    owner = path.parts[0] if path.parts else ""
    if owner not in IMPORT_RULES:
        return []
    try:
        tree = ast.parse((root / path).read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [f"{path}:{exc.lineno}: syntax error prevents import-boundary analysis"]
    allowed = IMPORT_RULES[owner]
    violations = []
    for line, imported, node in imported_nodes(tree, path):
        if imported not in PROJECT_ROOTS or imported in allowed:
            continue
        if owner == "core" and imported == "intelligence_modules" and is_absolute_loader_import(node):
            continue
        violations.append(f"{path}:{line}: {owner} must not import {imported}")
    return violations


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    violations = [
        violation
        for path in changed_python_paths(root)
        for violation in violations_for(path, root)
    ]
    if not violations:
        print("Import-boundary check: no violations in changed Python files.")
        return 0
    print("Import-boundary check: violations found:")
    print("\n".join(f"  {violation}" for violation in violations))
    return 1


if __name__ == "__main__":
    sys.exit(main())
