#!/usr/bin/env python3
"""Run registered read-only generated-artifact ownership checks."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

CHECKS = ("scripts/check_container_commander_bundle_freshness.py",)

def main():
    root = Path(__file__).resolve().parents[1]; failed = []
    for relative in CHECKS:
        result = subprocess.run([sys.executable, "-B", relative], cwd=root, text=True, capture_output=True)
        print(f"--- {relative} ---")
        print(result.stdout.rstrip())
        if result.returncode: failed.append(relative)
    print("Generated-output ownership check: REVIEW_REQUIRED drift found." if failed else "Generated-output ownership check: all registered checks passed.")
    return 0

if __name__ == "__main__": raise SystemExit(main())
