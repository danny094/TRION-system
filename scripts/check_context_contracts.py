#!/usr/bin/env python3
"""Report context-dictionary producer and consumer candidates without editing code."""
from __future__ import annotations
import argparse, os, re, subprocess
from pathlib import Path

ROOTS = ("adapters", "core", "mcp", "tools")
SUFFIXES = {".py", ".ts", ".tsx"}
SKIP = {".git", ".venv", "node_modules", "__pycache__"}
WRITE = re.compile(r"\b(routing_frame|orchestrator_context)\s*(?:\[\s*['\"]([^'\"]+)['\"]\s*\]|)\s*=")
OWNERS = {
    "routing_frame": ("core/routing_frame/", "core/pipeline/"),
    "orchestrator_context": ("core/pipeline/orchestrator_stage.py", "core/pipeline/runner.py"),
}

def changed(root):
    paths = set()
    for args in (["diff", "--name-only"], ["diff", "--cached", "--name-only"], ["ls-files", "--others", "--exclude-standard"]):
        out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout
        paths |= {Path(line) for line in out.splitlines() if line.strip()}
    return sorted(p for p in paths if p.parts and p.parts[0] in ROOTS and p.suffix in SUFFIXES and (root / p).is_file())

def all_paths(root):
    result = []
    for name in ROOTS:
        for directory, names, files in os.walk(root / name):
            names[:] = [item for item in names if item not in SKIP]
            result += [Path(directory, item).relative_to(root) for item in files if Path(item).suffix in SUFFIXES]
    return sorted(result)

def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--all", action="store_true")
    args = parser.parse_args(); root = Path(__file__).resolve().parents[1]
    rows = []
    for path in all_paths(root) if args.all else changed(root):
        for line_no, line in enumerate((root / path).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if match := WRITE.search(line):
                owner = match.group(1)
                location = path.as_posix()
                if not any(location.startswith(prefix) for prefix in OWNERS[owner]):
                    key = match.group(2) or "<whole object>"
                    rows.append(f"context_producer {path}:{line_no} {owner}[{key}] outside expected owner")
    print("Context-contract check: " + ("REVIEW_REQUIRED candidates:" if rows else "no candidates in scope."))
    if rows: print("\n".join(f"  {row}" for row in rows))
    return 0

if __name__ == "__main__": raise SystemExit(main())
