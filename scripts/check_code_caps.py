#!/usr/bin/env python3
"""Check the mandatory Doc07 200-line cap for changed code files.

This mechanical builder preflight reads Git metadata and the working tree. It
is not an audit, test, lifecycle, or human DECIDE substitute.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LINE_CAP = 200
CODE_SUFFIXES = frozenset({".py", ".ts", ".tsx", ".js", ".css", ".html", ".sh"})


def git_paths(args: list[str], root: Path) -> set[Path]:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return {Path(line) for line in result.stdout.splitlines() if line.strip()}


def changed_code_paths(root: Path) -> list[Path]:
    paths = git_paths(["diff", "--name-only"], root)
    paths |= git_paths(["diff", "--cached", "--name-only"], root)
    paths |= git_paths(["ls-files", "--others", "--exclude-standard"], root)
    return sorted(path for path in paths if path.suffix in CODE_SUFFIXES)


def line_count(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for _ in handle)
    except FileNotFoundError:
        return 0


def before_line_count(path: Path, root: Path) -> int:
    result = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=root, capture_output=True, text=True)
    return len(result.stdout.splitlines()) if result.returncode == 0 else 0


def find_violations(root: Path) -> list[tuple[Path, int, int]]:
    violations = []
    for path in changed_code_paths(root):
        after = line_count(root / path)
        if after > LINE_CAP:
            violations.append((path, before_line_count(path, root), after))
    return violations


def main(root: Path | None = None) -> int:
    root = root or Path.cwd()
    violations = find_violations(root)
    if not violations:
        print(f"Code-cap check: changed code files are <= {LINE_CAP} lines.")
        return 0
    print(f"Code-cap check: {len(violations)} violation(s) of {LINE_CAP} lines:")
    for path, before, after in violations:
        print(f"  {path}: before={before} after={after}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
