#!/usr/bin/env python3
"""Run the read-only pipeline preflights without adding scanner logic."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

CHECKS = (
    ("check_shadow_authorities.py", True),
    ("check_context_contracts.py", True),
    ("check_mcp_descriptor_chain.py", True),
    ("check_contract_writer_ownership.py", False),
    ("check_guard_test_evidence.py", False),
)


def write_child_output(output: str) -> None:
    if output:
        print(output, end="" if output.endswith("\n") else "\n")


def run_checks(root: Path, include_all: bool) -> int:
    failed = False
    for script_name, supports_all in CHECKS:
        argv = [sys.executable, "-B", str(root / "scripts" / script_name)]
        if include_all and supports_all:
            argv.append("--all")
        print(f"=== {script_name} ===")
        result = subprocess.run(argv, cwd=root, capture_output=True, text=True, check=False)
        write_child_output(result.stdout)
        write_child_output(result.stderr)
        if result.returncode:
            failed = True
            print(f"Pipeline-contract check: technical child failure: {script_name} exited {result.returncode}.")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="forward to child checks that support it")
    args = parser.parse_args()
    return run_checks(Path(__file__).resolve().parents[1], args.all)


if __name__ == "__main__":
    raise SystemExit(main())
