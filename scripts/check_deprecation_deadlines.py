#!/usr/bin/env python3
"""Check DEPRECATED YYYY-MM-DD markers against the Doc36 30-day limit.

The check reports evidence only. It never removes deprecated code or edits a
deadline; an expired marker remains a human consolidation decision.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

SCAN_SUFFIXES = {".md", ".py", ".ts", ".tsx", ".json", ".yml", ".yaml"}
SCAN_ROOTS = (
    "adapters", "config", "core", "docs", "examples", "intelligence_modules",
    "mcp", "mcp-servers", "memory", "personas", "plugins", "scripts", "tools", "utils",
)
SKIPPED_DIRS = {".git", ".venv", "node_modules", "__pycache__"}
MARKER = re.compile(r"\bDEPRECATED\s*:?\s*(\d{4}-\d{2}-\d{2})\b")
INLINE_CODE = re.compile(r"`[^`]*`")


def source_files(root: Path) -> list[Path]:
    paths = []
    for name in SCAN_ROOTS:
        start = root / name
        if not start.is_dir():
            continue
        for directory, names, files in os.walk(start):
            names[:] = [name for name in names if name not in SKIPPED_DIRS]
            paths.extend(Path(directory) / item for item in files if Path(item).suffix in SCAN_SUFFIXES)
    return sorted(paths)


def findings(root: Path, today: date) -> list[str]:
    limit = today + timedelta(days=30)
    result = []
    for path in source_files(root):
        in_fence = False
        for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if path.suffix == ".md" and line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            source = INLINE_CODE.sub("", line) if path.suffix == ".md" else line
            for raw_date in MARKER.findall(source):
                try:
                    deadline = date.fromisoformat(raw_date)
                except ValueError:
                    result.append(f"{path.relative_to(root)}:{line_number}: invalid deadline {raw_date}")
                    continue
                if deadline < today:
                    result.append(f"{path.relative_to(root)}:{line_number}: expired on {deadline}")
                elif deadline > limit:
                    result.append(f"{path.relative_to(root)}:{line_number}: exceeds 30-day limit ({deadline})")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    issues = findings(root, args.today)
    if not issues:
        print("Deprecation deadline check: no expired or overlong markers found.")
        return 0
    print("Deprecation deadline check: consolidation review required:")
    print("\n".join(f"  {issue}" for issue in issues))
    return 1


if __name__ == "__main__":
    sys.exit(main())
