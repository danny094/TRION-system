import asyncio
import importlib
import sys
from pathlib import Path

from fastapi import WebSocketDisconnect


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"
VENDOR_DIR = ADMIN_API_DIR / "vendor"


def _load_module(name: str):
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    if str(VENDOR_DIR) not in sys.path:
        sys.path.insert(0, str(VENDOR_DIR))
    module = importlib.import_module(name)
    return importlib.reload(module)


def test_ws_activity_slice_no_longer_imports_vendor_ws_stream():
    approval_store = (ADMIN_API_DIR / "commander_approval_store.py").read_text()
    operations = (ADMIN_API_DIR / "commander_api" / "operations.py").read_text()
    containers = (ADMIN_API_DIR / "commander_api" / "containers.py").read_text()

    assert "from container_commander.ws_stream import emit_activity" not in approval_store
    assert "from container_commander.ws_stream import ws_handler" not in operations
    assert "from container_commander.ws_stream import emit_activity" not in containers


def test_ws_handler_registers_client_and_emit_activity_broadcasts():
    activity = _load_module("commander_ws_activity")

    class _FakeWebSocket:
        def __init__(self):
            self.accepted = False
            self.sent = []
            self._reads = 0

        async def accept(self):
            self.accepted = True

        async def receive_text(self):
            if self._reads == 0:
                self._reads += 1
                await asyncio.sleep(0.05)
                raise WebSocketDisconnect()
            raise WebSocketDisconnect()

        async def send_json(self, payload):
            self.sent.append(payload)

    async def _run():
        websocket = _FakeWebSocket()
        task = asyncio.create_task(activity.ws_handler(websocket))
        await asyncio.sleep(0.01)
        activity.emit_activity("approval_requested", level="warn", message="Need approval", approval_id="a1")
        await asyncio.sleep(0.01)
        await task
        return websocket

    websocket = asyncio.run(_run())
    assert websocket.accepted is True
    assert websocket.sent == [
        {
            "event": "approval_requested",
            "level": "warn",
            "message": "Need approval",
            "data": {"approval_id": "a1"},
        }
    ]


def test_deploy_runtime_client_uses_local_ws_activity_and_runtime_preflight():
    runtime_client = _load_module("commander_deploy_runtime_client")

    events = []
    runtime_client.emit_activity = lambda event, level="info", message="", **data: events.append(
        {"event": event, "level": level, "message": message, "data": data}
    )

    runtime_client.emit_ws_activity("deploy_start", level="info", message="Starting", blueprint_id="bp1")
    assert events == [
        {
            "event": "deploy_start",
            "level": "info",
            "message": "Starting",
            "data": {"blueprint_id": "bp1"},
        }
    ]

    class _Client:
        def info(self):
            return {"Runtimes": {"nvidia": {}}}

    ok, reason = runtime_client.validate_runtime_preflight(_Client(), "nvidia")
    assert ok is True
    assert reason == "ok"


def test_deploy_runtime_client_builds_local_client_without_engine_import(monkeypatch):
    runtime_client = _load_module("commander_deploy_runtime_client")

    class _Networks:
        def __init__(self):
            self.created = None

        def get(self, name):
            raise runtime_client.NotFound("missing")

        def create(self, name, **kwargs):
            self.created = (name, kwargs)

    class _DockerClient:
        def __init__(self):
            self.networks = _Networks()

    class _DockerModule:
        @staticmethod
        def from_env():
            return _DockerClient()

    runtime_client._client = None
    monkeypatch.setattr(runtime_client, "docker", _DockerModule())

    client = runtime_client.get_runtime_client()

    assert client is not None
    assert client.networks.created[0] == runtime_client.NETWORK_NAME
