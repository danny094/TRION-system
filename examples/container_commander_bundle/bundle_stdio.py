#!/usr/bin/env python3
import json

import bundle_dispatch


def run_stdio_loop():
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
        print(json.dumps(bundle_dispatch.handle_request(payload)), flush=True)
