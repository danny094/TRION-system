#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from container_commander_bundle_gen.render_bundle import write_bundle
from container_commander_bundle_gen.source_ast import load_context


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="build/generated_bundle")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    context = load_context(root, root / args.out)
    write_bundle(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
