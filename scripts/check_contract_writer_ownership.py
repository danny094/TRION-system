#!/usr/bin/env python3
"""Report potential writes to registry, evidence, and conversation-state contracts."""
from __future__ import annotations
import os, re
from pathlib import Path

ROOTS = ("adapters", "core", "mcp", "memory", "tools")
TARGET = re.compile(r"mcp_registry|tool_intents|OutputEvidenceHandoff|conversation_meta", re.I)
WRITE = re.compile(r"write_|json\.dump|os\.replace|upsert|save|append|insert", re.I)

def main():
    root = Path(__file__).resolve().parents[1]; rows = []
    for name in ROOTS:
        for path in (root / name).rglob("*.py"):
            if {".venv", "__pycache__"}.intersection(path.parts): continue
            for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if TARGET.search(line) and WRITE.search(line): rows.append(f"contract_writer {path.relative_to(root)}:{line_no} {line.strip()[:100]}")
    print("Contract-writer ownership check: REVIEW_REQUIRED candidates:" if rows else "Contract-writer ownership check: no candidates.")
    if rows: print("\n".join(f"  {row}" for row in rows))
    return 0

if __name__ == "__main__": raise SystemExit(main())
