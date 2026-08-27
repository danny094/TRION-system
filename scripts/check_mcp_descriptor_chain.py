#!/usr/bin/env python3
"""Inventory MCP capability-field projections across the full descriptor-chain scope."""
from __future__ import annotations
import argparse, os, re
from pathlib import Path

ROOTS = ("mcp", "adapters", "core", "tools")
FIELDS = ("capability_domain", "capability_operation", "capability_output_schema", "target_scopes", "tool_role", "tool_intent_meta")
SUFFIXES = {".py", ".ts", ".tsx"}
FIELD = re.compile(r"\b(" + "|".join(FIELDS) + r")\b")

def paths(root):
    result = []
    for name in ROOTS:
        for path in (root / name).rglob("*"):
            if path.is_file() and path.suffix in SUFFIXES and not {".venv", "node_modules", "__pycache__"}.intersection(path.parts): result.append(path.relative_to(root))
    return sorted(result)

def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--all", action="store_true", help="kept for a uniform check interface")
    parser.parse_args(); root = Path(__file__).resolve().parents[1]; seen = {field: [] for field in FIELDS}
    for path in paths(root):
        for line_no, line in enumerate((root / path).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if match := FIELD.search(line): seen[match.group(1)].append(f"{path}:{line_no}")
    rows = [f"descriptor_field {field}: {len(locations)} occurrence(s)" for field, locations in seen.items() if locations]
    print("MCP descriptor-chain inventory (review field ownership before changing a projection):")
    print("\n".join(f"  {row}" for row in rows) if rows else "  no tracked capability fields found")
    return 0

if __name__ == "__main__": raise SystemExit(main())
