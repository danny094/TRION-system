#!/usr/bin/env python3
"""Report backend and WebUI chat-event literals each absent from Doc10."""
from __future__ import annotations
import os, re
from pathlib import Path

EVENT = re.compile(r"['\"]type['\"]\s*:\s*['\"]([A-Za-z_][\w-]*)['\"]")
CHAT_EVENT_TYPE = re.compile(r"export\s+type\s+ChatEventType\s*=\s*(.*?)(?:\n\n|$)", re.DOTALL)
STRING_LITERAL = re.compile(r"'([A-Za-z_][\w-]*)'")
CONTRACT_EVENT = re.compile(r"^\|\s*`([A-Za-z_][\w-]*)`\s*\|", re.MULTILINE)
SKIP = {"node_modules", ".venv", "__pycache__"}

def literals(root, base, suffixes):
    found = set()
    for directory, names, files in os.walk(root / base):
        names[:] = [name for name in names if name not in SKIP]
        for name in files:
            if Path(name).suffix in suffixes: found |= set(EVENT.findall(Path(directory, name).read_text(encoding="utf-8", errors="replace")))
    return found

def file_literals(path):
    return set(EVENT.findall(path.read_text(encoding="utf-8", errors="replace")))

def webui_event_types(path):
    match = CHAT_EVENT_TYPE.search(path.read_text(encoding="utf-8", errors="replace"))
    if not match:
        raise ValueError("ChatEventType alias not found in WebUI contract")
    return set(STRING_LITERAL.findall(match.group(1)))

def main():
    root = Path(__file__).resolve().parents[1]
    contract = set(CONTRACT_EVENT.findall((root / "docs/contracts/10-chat-event-contract.md").read_text(encoding="utf-8")))
    backend = literals(root, "core/pipeline", {".py"}) | literals(root, "core/task_loop", {".py"})
    backend |= file_literals(root / "adapters/admin-api/chat_routes.py")
    backend |= file_literals(root / "adapters/admin-api/chat_stream.py")
    webui_contract = webui_event_types(root / "adapters/webui/src/lib/contracts/chatEvents.ts")
    rows = [f"backend_event_not_in_doc10 {value}" for value in sorted(backend - contract)]
    rows += [f"webui_event_not_in_doc10 {value}" for value in sorted(webui_contract - contract)]
    print("Event-contract parity check: REVIEW_REQUIRED contract mismatches:" if rows else "Event-contract parity check: no static Doc10 mismatches.")
    if rows: print("\n".join(f"  {row}" for row in rows))
    return 0

if __name__ == "__main__": raise SystemExit(main())
