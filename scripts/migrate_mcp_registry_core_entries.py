#!/usr/bin/env python3
"""Explicitly migrate persisted MCP IDs that are now canonical core MCPs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.config import get_registry_path
from mcp.installer_registry import migrate_legacy_core_entries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create a backup and atomically remove current core IDs.",
    )
    args = parser.parse_args(argv)
    try:
        report = migrate_legacy_core_entries(apply=args.apply)
    except (OSError, UnicodeError, ValueError) as exc:
        report = {
            "status": "error",
            "mode": "apply" if args.apply else "dry_run",
            "registry_path": str(get_registry_path()),
            "error": str(exc),
        }
        print(json.dumps(report, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
