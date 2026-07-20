#!/usr/bin/env python3
import json
from datetime import datetime, timezone


TOOLS = [
    {
        "name": "time_now",
        "description": "Return the current UTC timestamp and local date data.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    }
]


def handle_request(payload):
    method = payload.get("method", "")
    request_id = payload.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "time-mcp", "version": "1.0.0"},
                "capabilities": {"tools": {"listChanged": False}},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = ((payload.get("params") or {}).get("name") or "").strip()
        if name != "time_now":
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}
        now = datetime.now(timezone.utc)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "utc_iso": now.isoformat(),
                "unix": int(now.timestamp()),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "timezone": "UTC",
            },
        }
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main():
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
        response = handle_request(payload)
        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
