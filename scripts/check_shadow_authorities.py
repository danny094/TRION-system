#!/usr/bin/env python3
"""Report advisory, document-referenced shadow-authority candidates only."""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
from pathlib import Path
CODE_SUFFIXES = {".py", ".ts", ".tsx"}
SOURCE_ROOTS = ("adapters", "config", "core", "examples", "mcp", "mcp-servers", "memory", "tools", "utils")
SIGNALS = ("live_claim", "dialogue_signal", "operation_contract", "execution_mode")
SIGNAL_ASSIGNMENT = re.compile(r"\b(" + "|".join(SIGNALS) + r")\b[^=]*=", re.I)
TOOL_DECLARATION = re.compile(r"^\s*[A-Z][A-Z0-9_]*(?:TOOL|TOOLS|MCP|MCPS|SKILL|SKILLS)[A-Z0-9_]*\s*=\s*[\[{(]")
REGISTRY_WRITE = re.compile(r"(?:mcp_registry|registry_path).*(?:write_|json\.dump|os\.replace|atomic_write)|(?:write_|json\.dump|os\.replace|atomic_write).*(?:mcp_registry|registry_path)")
SIGNAL_OWNERS = {"live_claim": ("core/classifier/", "core/routing_frame/"), "dialogue_signal": ("core/dialogue_signal/", "core/routing_frame/"), "operation_contract": ("core/routing_frame/",), "execution_mode": ("core/routing_frame/",)}
ALIAS_OWNER = {
    "mcp-servers/container-commander/contracts.py": "normalize_container_reference"
}
ALIAS_PROJECTIONS = {
    "examples/container_commander_bundle/bundle_dispatch.py":
        "normalize_container_reference"
}
FRAME_READERS = {"dialogue_signal_from_frame", "live_claim_from_frame"}
OWNER_MAP_REFERENCE = "docs/implementation-plans/active/p17-container-commander-contract-consolidation.md:263"
def git_paths(args: list[str], root: Path) -> set[Path]:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return {Path(line) for line in result.stdout.splitlines() if line.strip()}
def scoped_paths(root: Path, paths: set[Path]) -> list[Path]:
    return sorted(path for path in paths if path.parts and path.parts[0] in SOURCE_ROOTS and path.suffix in CODE_SUFFIXES and (root / path).is_file())
def changed_paths(root: Path) -> list[Path]:
    paths = git_paths(["diff", "--name-only"], root)
    paths |= git_paths(["diff", "--cached", "--name-only"], root)
    paths |= git_paths(["ls-files", "--others", "--exclude-standard"], root)
    return scoped_paths(root, paths)
def all_paths(root: Path) -> list[Path]:
    return scoped_paths(root, git_paths(["ls-files"], root))
def is_signal_owner(path: Path, signal: str) -> bool:
    normalized = f"{path.as_posix()}/"
    return any(normalized.startswith(owner) for owner in SIGNAL_OWNERS[signal])
def is_alias_owner(path: Path, function_name: str | None) -> bool:
    owner = ALIAS_OWNER.get(path.as_posix())
    projection = ALIAS_PROJECTIONS.get(path.as_posix())
    return function_name is not None and function_name in {owner, projection}
def names_in(node: ast.AST) -> set[str]:
    return {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}
def is_frame_projection(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "routing_frame"
    if isinstance(node, (ast.Attribute, ast.Subscript)):
        return is_frame_projection(node.value)
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        projections = [is_frame_projection(value) for value in node.values]
        return any(projections) and all(
            projected or isinstance(value, ast.Constant) and value.value in (None, "", False)
            for projected, value in zip(projections, node.values)
        )
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Attribute) and is_frame_projection(node.func.value):
        return True
    function_name = node.func.id if isinstance(node.func, ast.Name) else ""
    if function_name == "str":
        return any(is_frame_projection(argument) for argument in node.args)
    return function_name in FRAME_READERS and any(isinstance(argument, ast.Name) and argument.id == "frame" for argument in node.args)
def assignment_names(node: ast.Assign | ast.AnnAssign) -> set[str]:
    targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
    return {target.id for target in targets if isinstance(target, ast.Name)}
class AuthorityVisitor(ast.NodeVisitor):
    def __init__(self, path: Path):
        self.path = path
        self.rows: list[str] = []
        self.functions: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None: self.visit_FunctionDef(node)
    def visit_Assign(self, node: ast.Assign) -> None:
        self._check_signal_assignment(assignment_names(node), node.value, node.lineno)
        self.generic_visit(node)
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._check_signal_assignment(assignment_names(node), node.value, node.lineno)
        self.generic_visit(node)
    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        if isinstance(node.op, ast.Or):
            self._check_alias(node, node.lineno)
        self.generic_visit(node)
    def visit_IfExp(self, node: ast.IfExp) -> None:
        self._check_alias(node, node.lineno)
        self.generic_visit(node)
    def _check_signal_assignment(self, targets: set[str], value: ast.AST, line: int) -> None:
        for signal in sorted(targets.intersection(SIGNALS)):
            if not is_signal_owner(self.path, signal) and not is_frame_projection(value):
                self.rows.append(f"routing_signal {self.path}:{line} {signal} re-derived outside documented owner")

    def _check_alias(self, node: ast.AST, line: int) -> None:
        function_name = self.functions[-1] if self.functions else None
        if {"container_id", "container_name"}.issubset(names_in(node)) and not is_alias_owner(self.path, function_name):
            self.rows.append(f"alias_selection {self.path}:{line} container_id/container_name outside documented owner")
def ast_findings(root: Path, path: Path) -> list[str]:
    try:
        tree = ast.parse((root / path).read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as error:
        return [f"syntax_error {path}:{error.lineno} unable to inspect authority candidates"]
    visitor = AuthorityVisitor(path)
    visitor.visit(tree)
    return visitor.rows
def text_findings(root: Path, path: Path) -> list[str]:
    rows = []
    for line_number, line in enumerate((root / path).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        signal_match = SIGNAL_ASSIGNMENT.search(line)
        if path.suffix != ".py" and signal_match and "routing_frame" not in line and not is_signal_owner(path, signal_match.group(1).lower()):
            rows.append(f"routing_signal {path}:{line_number} {signal_match.group(1).lower()} re-derived outside documented owner")
        if TOOL_DECLARATION.search(line):
            rows.append(f"tool_truth {path}:{line_number} hardcoded tool/skill/MCP declaration")
        if REGISTRY_WRITE.search(line):
            rows.append(f"registry_writer {path}:{line_number} possible registry write path")
    return rows
def findings(root: Path, paths: list[Path]) -> list[str]:
    rows = []
    for path in paths:
        if path.suffix == ".py":
            rows.extend(ast_findings(root, path))
        rows.extend(text_findings(root, path))
    return rows
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="scan tracked code in every defined source root")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    rows = findings(root, all_paths(root) if args.all else changed_paths(root))
    if not rows:
        print("Shadow-authority check: no candidates in scope.")
        return 0
    print(f"Shadow-authority check ({OWNER_MAP_REFERENCE}): REVIEW_REQUIRED candidates:")
    print("\n".join(f"  {row}" for row in rows))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
