#!/usr/bin/env python3
"""Report changed guard functions with no literal reference in tests/."""
from __future__ import annotations
import re, subprocess
from pathlib import Path

GUARD = re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*(?:guard|fallback|validate)\w*)\s*\(")

def changed_python(root):
    paths = set()
    for args in (
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
        paths.update(Path(line) for line in result.stdout.splitlines() if line.strip())
    return sorted(
        path
        for path in paths
        if path.parts
        and path.parts[0] in {"core", "adapters", "mcp", "tools"}
        and path.suffix == ".py"
        and (root / path).is_file()
    )

def main():
    root = Path(__file__).resolve().parents[1]; tests = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (root / "tests").glob("test_*.py"))
    rows = []
    for path in changed_python(root):
        for line_no, line in enumerate((root / path).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if match := GUARD.match(line):
                if match.group(1) not in tests: rows.append(f"guard_test {path}:{line_no} {match.group(1)} has no literal test reference")
    print("Guard-test evidence check: REVIEW_REQUIRED candidates:" if rows else "Guard-test evidence check: no candidates in scope.")
    if rows: print("\n".join(f"  {row}" for row in rows))
    return 0

if __name__ == "__main__": raise SystemExit(main())
