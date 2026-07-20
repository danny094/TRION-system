import asyncio
import importlib
import sys
from pathlib import Path


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


class _FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def test_exec_runtime_slice_no_longer_imports_engine_helpers_directly():
    source = (ADMIN_API_DIR / "commander_api" / "containers.py").read_text()
    runtime_source = (ADMIN_API_DIR / "commander_container_runtime.py").read_text()
    assert "from container_commander.engine import exec_in_container" not in source
    assert "from container_commander.engine import (" not in source or "exec_in_container_detailed" not in source
    assert "from container_commander.engine import get_container_stats" not in source
    assert "from container_commander.engine import get_quota" not in source
    assert "from container_commander.engine import cleanup_all" not in source
    assert "from container_commander.engine import get_client" not in source
    assert "from container_commander.engine.observe import get_container_logs" not in runtime_source
    assert "from container_commander.engine.observe import get_container_stats" not in runtime_source
    assert "from container_commander.engine.state import cleanup_all" not in runtime_source
    assert "from container_commander.engine.quota import get_quota" not in runtime_source


def test_exec_runtime_routes_use_local_runtime_facade(monkeypatch):
    containers = _load_module("commander_api.containers")

    monkeypatch.setattr(containers, "exec_in_container", lambda container_id, command, timeout=30: (0, "ok"), raising=False)
    monkeypatch.setattr(
        containers,
        "exec_in_container_detailed",
        lambda container_id, command, timeout=30: {
            "exit_code": 0,
            "stdout": "diag out",
            "stderr": "",
            "truncated": False,
            "container_id": container_id,
        },
        raising=False,
    )
    monkeypatch.setattr(
        containers,
        "inspect_container_via_mcp",
        lambda container_id: {
            "container_id": "cid-1",
            "name": "demo",
            "status": "running",
            "blueprint_id": "bp-demo",
            "image": "python:3.12",
        },
        raising=False,
    )
    monkeypatch.setattr(containers, "get_container_stats", lambda container_id: {"cpu_percent": 2.5, "memory_mb": 128}, raising=False)
    monkeypatch.setattr(containers, "get_container_logs", lambda container_id, tail=100: "hello logs", raising=False)
    monkeypatch.setattr(containers, "_remember_container_state", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(
        containers,
        "_complete_commander_chat",
        lambda messages, fallback_text: asyncio.sleep(0, result={"content": "Findings\nCause\nChecks", "provider": "ollama", "requested_provider": "ollama", "model": "demo"}),
        raising=False,
    )
    monkeypatch.setattr(containers, "get_quota", lambda: type("Quota", (), {"model_dump": lambda self: {"containers_used": 1}})(), raising=False)
    monkeypatch.setattr(containers, "cleanup_all", lambda: None, raising=False)

    executed = asyncio.run(containers.api_exec_in_container("cid-1", _FakeRequest({"command": "pwd", "timeout": 5})))
    debugged = asyncio.run(containers.api_trion_debug_container("cid-1", _FakeRequest({"task": "check app"})))
    stats = asyncio.run(containers.api_container_stats("cid-1"))
    quota = asyncio.run(containers.api_get_quota())
    cleaned = asyncio.run(containers.api_cleanup_all())

    assert executed == {"executed": True, "exit_code": 0, "output": "ok"}
    assert debugged["analyzed"] is True
    assert debugged["context"]["diag_executed"] is True
    assert stats == {"cpu_percent": 2.5, "memory_mb": 128}
    assert quota == {"containers_used": 1}
    assert cleaned == {"cleaned": True}


def test_runtime_facade_uses_mcp_quota_contract(monkeypatch):
    runtime = _load_module("commander_container_runtime")
    monkeypatch.setattr(
        runtime,
        "get_runtime_quota_via_mcp",
        lambda: {
            "max_containers": 5,
            "max_total_memory_mb": 2048,
            "max_total_cpu": 2.0,
            "containers_used": 1,
            "memory_used_mb": 512,
            "cpu_used": 1.0,
        },
        raising=False,
    )

    quota = runtime.get_quota()

    assert quota.model_dump() == {
        "max_containers": 5,
        "max_total_memory_mb": 2048,
        "max_total_cpu": 2.0,
        "containers_used": 1,
        "memory_used_mb": 512,
        "cpu_used": 1.0,
    }


def test_trion_shell_routes_use_mcp_inspect_metadata(monkeypatch):
    containers = _load_module("commander_api.containers")
    calls = {"inspect": 0}
    monkeypatch.setattr(
        containers,
        "inspect_container_via_mcp",
        lambda container_id: (
            calls.__setitem__("inspect", calls["inspect"] + 1)
            or {
                "container_id": "cid-1",
                "name": "demo",
                "status": "running",
                "blueprint_id": "bp-demo",
                "image": "python:3.12",
            }
        ),
        raising=False,
    )
    monkeypatch.setattr(containers, "_remember_container_state", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(containers, "_resolve_shell_language", lambda **kwargs: "de", raising=False)
    monkeypatch.setattr(
        containers,
        "_localized_labels",
        lambda language: {
            "shell_started": "started",
            "shell_stopped": "stopped",
            "empty_reply": "",
            "findings": "Findings",
            "likely_cause": "Cause",
            "next_checks": "Checks",
        },
        raising=False,
    )
    monkeypatch.setattr(containers, "_complete_commander_chat", lambda messages, fallback_text: asyncio.sleep(0, result={"content": "{\"goal\":\"\",\"findings\":[],\"actions_taken\":[],\"changes_made\":[],\"blocker\":\"\",\"next_step\":\"\"}", "provider": "ollama", "requested_provider": "ollama", "model": "demo"}), raising=False)
    monkeypatch.setattr(containers, "_build_shell_step_messages", lambda **kwargs: [], raising=False)
    monkeypatch.setattr(containers, "_parse_shell_step_response", lambda text: {"assistant_text": "ok", "command": "", "action_type": "answer", "verification": {}, "stop_reason": "", "exit_shell": False}, raising=False)
    monkeypatch.setattr(containers, "_persist_shell_step", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(containers, "_remember_container_state", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(containers, "_collect_container_diagnostics", lambda *args, **kwargs: {"executed": False}, raising=False)

    async def _fake_mission_state(conversation_id):
        return "mission"

    async def _fake_load_addon_context(*args, **kwargs):
        return {"selected_docs": []}

    async def _fake_checkpoint(*args, **kwargs):
        return None

    async def _fake_summary(*args, **kwargs):
        return None

    monkeypatch.setitem(sys.modules, "commander_ws_activity", type("Ws", (), {"emit_activity": staticmethod(lambda *args, **kwargs: None)})())
    monkeypatch.setitem(sys.modules, "commander_shell_context", type("ShellCtx", (), {"build_mission_state": staticmethod(_fake_mission_state), "save_shell_checkpoint": staticmethod(_fake_checkpoint), "save_shell_session_summary": staticmethod(_fake_summary)})())
    monkeypatch.setitem(sys.modules, "intelligence_modules.container_addons.loader", type("AddonLoader", (), {"load_container_addon_context": staticmethod(_fake_load_addon_context)})())

    started = asyncio.run(containers.api_trion_shell_start("cid-1", _FakeRequest({"conversation_id": "conv-1", "goal": "check"})))
    stepped = asyncio.run(containers.api_trion_shell_step("cid-1", _FakeRequest({"conversation_id": "conv-1", "instruction": "next"})))
    stopped = asyncio.run(containers.api_trion_shell_stop("cid-1", _FakeRequest({"conversation_id": "conv-1"})))

    assert started["active"] is True
    assert stepped["active"] is True
    assert stopped["active"] is False
    assert calls["inspect"] >= 3
