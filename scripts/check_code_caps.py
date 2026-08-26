#!/usr/bin/env python3
"""Check the mandatory 200-line cap for changed code files.

This mechanical preflight reads Git metadata and the working tree. It is not
an audit, release decision, or substitute for tests and human review.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LINE_CAP = 200
CODE_SUFFIXES = frozenset({".py", ".ts", ".tsx", ".js", ".css", ".html", ".sh"})


def git_paths(args: list[str], root: Path) -> set[Path]:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return {Path(line) for line in result.stdout.splitlines() if line.strip()}


def staged_code_paths(root: Path) -> set[Path]:
    return {
        path
        for path in git_paths(["diff", "--cached", "--name-only"], root)
        if path.suffix in CODE_SUFFIXES
    }


def working_tree_code_paths(root: Path) -> set[Path]:
    paths = git_paths(["diff", "--name-only"], root)
    paths |= git_paths(["ls-files", "--others", "--exclude-standard"], root)
    return {path for path in paths if path.suffix in CODE_SUFFIXES}


def changed_code_paths(root: Path) -> list[Path]:
    return sorted(staged_code_paths(root) | working_tree_code_paths(root))


def line_count(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for _ in handle)
    except FileNotFoundError:
        return 0


def before_line_count(path: Path, root: Path) -> int:
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return len(result.stdout.splitlines()) if result.returncode == 0 else 0


def staged_line_count(path: Path, root: Path) -> int:
    result = subprocess.run(
        ["git", "show", f":{path}"],
        cwd=root,
        capture_output=True,
        text=True,
        errors="replace",
    )
    return len(result.stdout.splitlines()) if result.returncode == 0 else 0


def find_violations(root: Path) -> list[tuple[Path, int, int]]:
    violations = []
    staged_paths = staged_code_paths(root)
    working_tree_paths = working_tree_code_paths(root)
    for path in sorted(staged_paths | working_tree_paths):
        candidate_counts = []
        if path in staged_paths:
            candidate_counts.append(staged_line_count(path, root))
        if path in working_tree_paths:
            candidate_counts.append(line_count(root / path))
        after = max(candidate_counts, default=0)
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
