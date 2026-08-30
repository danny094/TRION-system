from __future__ import annotations

from dataclasses import dataclass
from typing import Any


LIST_DEFAULT_ENTRIES = 100
LIST_MAX_ENTRIES = 500
LIST_DEFAULT_DEPTH = 1
LIST_MAX_DEPTH = 8
SEARCH_DEFAULT_RESULTS = 50
SEARCH_MAX_RESULTS = 200
SEARCH_DEFAULT_DEPTH = 8
SEARCH_MAX_DEPTH = 32
READ_DEFAULT_BYTES = 65_536
READ_MAX_BYTES = 1_048_576


@dataclass
class FilesystemFailure(Exception):
    code: str
    message: str
    retryable: bool = False


def bounded_value(value: Any, *, default: int, hard_cap: int, field: str) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise FilesystemFailure("MALFORMED_REQUEST", f"{field} must be a positive integer")
    if value > hard_cap:
        raise FilesystemFailure("LIMIT_EXCEEDED", f"{field} exceeds hard cap {hard_cap}")
    return value


def success_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": "Filesystem request completed."}],
        "structuredContent": payload,
        "isError": False,
    }


def error_envelope(failure: FilesystemFailure) -> dict[str, Any]:
    error = {
        "code": failure.code,
        "message": failure.message,
        "retryable": failure.retryable,
    }
    return {
        "content": [{"type": "text", "text": failure.message}],
        "structuredContent": {"ok": False, "error": error},
        "isError": True,
    }


def object_schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def positive_integer_schema(maximum: int) -> dict[str, Any]:
    return {"type": "integer", "minimum": 1, "maximum": maximum}


ENTRY_SCHEMA = object_schema(
    {
        "relative_path": {"type": "string"},
        "entry_type": {"enum": ["file", "directory"]},
        "size_bytes": {"type": ["integer", "null"], "minimum": 0},
    },
    ["relative_path", "entry_type", "size_bytes"],
)

ERROR_SCHEMA = object_schema(
    {
        "ok": {"const": False},
        "error": object_schema(
            {
                "code": {"type": "string", "minLength": 1},
                "message": {"type": "string", "minLength": 1},
                "retryable": {"type": "boolean"},
            },
            ["code", "message", "retryable"],
        ),
    },
    ["ok", "error"],
)


def result_schema(success_schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "oneOf": [success_schema, ERROR_SCHEMA],
    }


def tool_definitions() -> list[dict[str, Any]]:
    path = {"type": "string"}
    complete = {"type": "boolean"}
    return [
        {
            "name": "filesystem_list",
            "description": "List bounded entries below TRION Home or inspect one exact target.",
            "inputSchema": object_schema(
                {"relative_path": path,
                 "max_entries": positive_integer_schema(LIST_MAX_ENTRIES),
                 "max_depth": positive_integer_schema(LIST_MAX_DEPTH)}, []
            ),
            "outputSchema": result_schema(object_schema(
                {
                    "entries": {"type": "array", "items": ENTRY_SCHEMA},
                    "complete": complete,
                    "truncated": complete,
                    "relative_path": path,
                    "exists": complete,
                },
                ["entries", "complete", "truncated"],
            )),
        },
        {
            "name": "filesystem_search",
            "description": "Search bounded root-relative filenames and paths below TRION Home.",
            "inputSchema": object_schema(
                {"query": {"type": "string", "minLength": 1}, "relative_path": path,
                 "max_results": positive_integer_schema(SEARCH_MAX_RESULTS),
                 "max_depth": positive_integer_schema(SEARCH_MAX_DEPTH)},
                ["query"],
            ),
            "outputSchema": result_schema(object_schema(
                {"query": {"type": "string"}, "matches": {"type": "array", "items": ENTRY_SCHEMA},
                 "complete": complete, "truncated": complete},
                ["query", "matches", "complete", "truncated"],
            )),
        },
        {
            "name": "filesystem_metadata",
            "description": "Return privacy-minimal metadata for one exact TRION Home target.",
            "inputSchema": object_schema({"relative_path": path}, ["relative_path"]),
            "outputSchema": result_schema(ENTRY_SCHEMA),
        },
        {
            "name": "filesystem_read",
            "description": "Read one bounded UTF-8 file below TRION Home.",
            "inputSchema": object_schema(
                {"relative_path": path,
                 "max_bytes": positive_integer_schema(READ_MAX_BYTES)}, ["relative_path"]
            ),
            "outputSchema": result_schema(object_schema(
                {"relative_path": path, "text": {"type": "string"},
                 "size_bytes": {"type": "integer", "minimum": 0},
                 "read_bytes": {"type": "integer", "minimum": 0},
                 "complete": complete, "truncated": complete},
                ["relative_path", "text", "size_bytes", "read_bytes", "complete", "truncated"],
            )),
        },
    ]
