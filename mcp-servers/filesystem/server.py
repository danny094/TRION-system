#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "filesystem"

from .contracts import FilesystemFailure, error_envelope, success_envelope, tool_definitions
from .listing import list_entries
from .metadata import metadata_for
from .reader import read_text
from .search import search_paths
from .settings import load_root


MCP_PROTOCOL_VERSION = "2024-11-05"
TOOLS = tool_definitions()


def handle_request(payload: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    request_id = payload.get("id")
    method = payload.get("method")
    if method == "initialize":
        return _response(
            request_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "serverInfo": {"name": "filesystem", "version": "1.0.0"},
                "capabilities": {"tools": {"listChanged": False}},
            },
        )
    if method == "tools/list":
        return _response(request_id, {"tools": TOOLS})
    if method != "tools/call":
        return _protocol_error(request_id, -32601, f"Method not found: {method}")
    params = payload.get("params")
    if not isinstance(params, dict):
        return _response(request_id, error_envelope(FilesystemFailure("MALFORMED_REQUEST", "params must be an object")))
    name = params.get("name")
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        return _response(request_id, error_envelope(FilesystemFailure("MALFORMED_REQUEST", "arguments must be an object")))
    handlers: dict[str, Callable[..., dict[str, object]]] = {
        "filesystem_list": list_entries,
        "filesystem_search": search_paths,
        "filesystem_metadata": metadata_for,
        "filesystem_read": read_text,
    }
    handler = handlers.get(str(name))
    if handler is None:
        return _protocol_error(request_id, -32601, f"Unknown tool: {name}")
    try:
        result = handler(root or load_root(), **arguments)
        return _response(request_id, success_envelope(result))
    except TypeError:
        failure = FilesystemFailure("MALFORMED_REQUEST", "arguments do not match the tool contract")
    except FilesystemFailure as caught:
        failure = caught
    return _response(request_id, error_envelope(failure))


def _response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _protocol_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def main() -> None:
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("method") == "notifications/initialized":
            continue
        print(json.dumps(handle_request(payload)), flush=True)


if __name__ == "__main__":
    main()
