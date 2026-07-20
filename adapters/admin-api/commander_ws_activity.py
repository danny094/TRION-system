from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Client:
    websocket: WebSocket
    loop: asyncio.AbstractEventLoop


_CLIENTS: set[_Client] = set()
_LOCK = threading.Lock()


def _payload(event: str, level: str = "info", message: str = "", **data: Any) -> dict[str, Any]:
    payload = {"event": str(event or "").strip(), "level": str(level or "info").strip(), "message": str(message or "")}
    if data:
        payload["data"] = data
    return payload


def _register_client(websocket: WebSocket, loop: asyncio.AbstractEventLoop) -> _Client:
    client = _Client(websocket=websocket, loop=loop)
    with _LOCK:
        _CLIENTS.add(client)
    return client


def _unregister_client(client: _Client) -> None:
    with _LOCK:
        _CLIENTS.discard(client)


def emit_activity(event: str, level: str = "info", message: str = "", **data: Any) -> None:
    payload = _payload(event, level=level, message=message, **data)
    with _LOCK:
        clients = list(_CLIENTS)
    stale: list[_Client] = []
    for client in clients:
        try:
            future = asyncio.run_coroutine_threadsafe(client.websocket.send_json(payload), client.loop)
            future.add_done_callback(lambda fut: fut.exception())
        except Exception as exc:
            logger.debug("[CommanderWS] emit failed: %s", exc)
            stale.append(client)
    for client in stale:
        _unregister_client(client)


async def ws_handler(websocket: WebSocket) -> None:
    await websocket.accept()
    client = _register_client(websocket, asyncio.get_running_loop())
    try:
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        _unregister_client(client)
