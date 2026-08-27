#!/usr/bin/env python3
"""Report prompt-building candidates and nearby provenance evidence.

This is deliberately advisory: a human or independent auditor decides whether
the source and filter named in a comment are semantically sufficient.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

CODE_SUFFIXES = {".py", ".ts", ".tsx"}
SKIPPED_DIRS = {".git", ".venv", "node_modules", "__pycache__"}
FUNCTION = re.compile(
    r"^\s*(?:async\s+)?(?:def|function|const)\s+([A-Za-z_]\w*(?:prompt|messages|dynamic_context))\b",
    re.IGNORECASE,
)
PROVENANCE = re.compile(r"provenance|source|filter|registry|live.discovery", re.IGNORECASE)


def git_paths(args: list[str], root: Path) -> set[Path]:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return {Path(line) for line in result.stdout.splitlines() if line.strip()}


def changed_paths(root: Path) -> list[Path]:
    paths = git_paths(["diff", "--name-only"], root)
    paths |= git_paths(["diff", "--cached", "--name-only"], root)
    paths |= git_paths(["ls-files", "--others", "--exclude-standard"], root)
    return sorted(path for path in paths if path.suffix in CODE_SUFFIXES and (root / path).is_file())


def all_paths(root: Path) -> list[Path]:
    paths = []
    for directory, names, files in os.walk(root):
        names[:] = [name for name in names if name not in SKIPPED_DIRS]
        paths.extend(Path(directory).joinpath(name).relative_to(root) for name in files if Path(name).suffix in CODE_SUFFIXES)
    return sorted(paths)


def candidates(root: Path, paths: list[Path]) -> list[str]:
    rows = []
    for path in paths:
        lines = (root / path).read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines):
            match = FUNCTION.match(line)
            if not match:
                continue
            context = "\n".join(lines[max(0, index - 8):index])
            status = "PROVENANCE_HINT" if PROVENANCE.search(context) else "REVIEW_REQUIRED"
            rows.append(f"{status} {path}:{index + 1} {match.group(1)}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="scan all project code instead of changed files")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    rows = candidates(root, all_paths(root) if args.all else changed_paths(root))
    if not rows:
        print("Prompt provenance report: no candidates in scope.")
        return 0
    print("Prompt provenance report (advisory, not a PASS/FAIL decision):")
    print("\n".join(f"  {row}" for row in rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
