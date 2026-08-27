"""Daily protocol storage helpers and graph merge execution."""

import json
import re
import threading
from pathlib import Path
from typing import Callable, Iterable

from mcp.tool_result_contracts import MCPToolCallStatus, MCPToolResultEnvelope


DATE_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_locks = {}
_locks_lock = threading.Lock()


def get_lock(filepath: Path) -> threading.Lock:
    with _locks_lock:
        key = str(filepath)
        if key not in _locks:
            _locks[key] = threading.Lock()
        return _locks[key]


def load_status(status_file: Path) -> dict:
    if status_file.exists():
        try:
            return json.loads(status_file.read_text())
        except Exception:
            return {}
    return {}


def save_status(status_file: Path, status: dict) -> None:
    status_file.write_text(json.dumps(status, indent=2))


def is_protocol_date_stem(stem: str) -> bool:
    return bool(DATE_FILE_RE.fullmatch(str(stem or "").strip()))


def parse_entries(content: str) -> list:
    parts = re.split(r"^(## \d{2}:\d{2})", content, flags=re.MULTILINE)
    entries = []
    index = 1
    while index < len(parts) - 1:
        entries.append((parts[index] + parts[index + 1]).strip())
        index += 2
    return entries


def reconstruct_md(date: str, entries: list) -> str:
    return f"# Tagesprotokoll {date}\n\n" + "\n\n".join(entries) + "\n"


def merge_entries(entries: Iterable[str], get_hub: Callable) -> tuple[int, list[str]]:
    merged_count = 0
    errors = []
    hub = get_hub()
    hub.initialize()
    for entry_text in entries:
        try:
            result = hub.call_tool("graph_add_node", {
                "source_type": "daily-protocol",
                "content": entry_text,
                "conversation_id": "daily-protocol",
                "confidence": 0.85,
            })
            if not isinstance(result, MCPToolResultEnvelope):
                errors.append("invalid_tool_result")
            elif result.status is MCPToolCallStatus.SUCCESS:
                merged_count += 1
            else:
                errors.append(result.status.name.lower())
        except Exception as error:
            errors.append(str(error))
    return merged_count, errors
