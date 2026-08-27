#!/usr/bin/env python3
"""Project the canonical MCP protocol version into self-contained bundles."""

from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "mcp" / "protocol_negotiation_contracts.py"
TIME_BUNDLE_PATH = ROOT / "examples" / "time_mcp_bundle" / "server.py"
PROJECTION_PATTERN = re.compile(r'^(MCP_PROTOCOL_VERSION\s*=\s*)"[^"]*"$', re.MULTILINE)


def read_protocol_version_literal(source_path: Path = SOURCE_PATH) -> str:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    values = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == "SUPPORTED_MCP_PROTOCOL_VERSION":
            values.append(ast.literal_eval(node.value))
    if len(values) != 1 or not isinstance(values[0], str) or not values[0]:
        raise ValueError("canonical MCP protocol version must be one non-empty string literal")
    return values[0]


def project_protocol_version_literals(
    source_path: Path = SOURCE_PATH,
    target_paths: tuple[Path, ...] = (TIME_BUNDLE_PATH,),
) -> str:
    version = read_protocol_version_literal(source_path)
    for target_path in target_paths:
        current = target_path.read_text(encoding="utf-8")
        projected, count = PROJECTION_PATTERN.subn(
            lambda match: f'{match.group(1)}"{version}"',
            current,
        )
        if count != 1:
            raise ValueError(f"expected one MCP protocol projection in {target_path}")
        target_path.write_text(projected, encoding="utf-8")
    return version


def main() -> int:
    project_protocol_version_literals()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
