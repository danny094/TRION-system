import asyncio
import importlib
import sys
import types
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


def test_shell_context_slice_no_longer_imports_vendor_bridge():
    containers = (ADMIN_API_DIR / "commander_api" / "containers.py").read_text()
    assert "from container_commander.shell_context_bridge import save_shell_checkpoint" not in containers
    assert "from container_commander.shell_context_bridge import build_mission_state" not in containers
    assert "from container_commander.shell_context_bridge import save_shell_session_summary" not in containers


def test_shell_context_builds_mission_state_and_persists_events(monkeypatch):
    shell_context = _load_module("commander_shell_context")
    calls = []

    class _FakeHub:
        def initialize(self):
            return None

        def call_tool(self, tool_name, args):
            calls.append((tool_name, args))
            if tool_name == "workspace_event_list":
                return {
                    "events": [
                        {
                            "event_type": "trion_shell_checkpoint",
                            "event_data": {
                                "goal": "Check nginx",
                                "finding": "nginx failed",
                                "action_taken": "cat /var/log/nginx/error.log",
                                "blocker": "",
                            },
                        },
                        {
                            "event_type": "trion_shell_session_summary",
                            "event_data": {
                                "goal": "Fix service",
                                "raw_summary": "Restarted supervisor and confirmed recovery.",
                            },
                        },
                    ]
                }
            return {"ok": True}

    fake_hub_module = types.ModuleType("mcp.hub")
    fake_hub_module.get_hub = lambda: _FakeHub()
    monkeypatch.setitem(sys.modules, "mcp.hub", fake_hub_module)

    mission_state = asyncio.run(shell_context.build_mission_state("conv-1"))
    assert "checkpoint: Check nginx | nginx failed | cat /var/log/nginx/error.log" in mission_state
    assert "summary: Fix service | Restarted supervisor and confirmed recovery." in mission_state

    asyncio.run(
        shell_context.save_shell_checkpoint(
            conversation_id="conv-1",
            container_id="c1",
            blueprint_id="bp1",
            goal="Check nginx",
            finding="nginx failed",
            action_taken="cat /var/log/nginx/error.log",
            blocker="",
            step_count=2,
            raw_summary="nginx failed\nCommand: cat /var/log/nginx/error.log",
        )
    )
    asyncio.run(
        shell_context.save_shell_session_summary(
            conversation_id="conv-1",
            container_id="c1",
            blueprint_id="bp1",
            container_name="demo",
            goal="Fix service",
            findings="Found broken config",
            changes_applied="Updated config",
            open_blocker="",
            step_count=3,
            commands=["cat /etc/demo.conf", "vi /etc/demo.conf"],
            user_requests=["Please fix the service"],
            final_stop_reason="done",
            summary_parts={"goal": "Fix service"},
            raw_summary="Service fixed",
        )
    )

    saved = [item for item in calls if item[0] == "workspace_event_save"]
    assert len(saved) == 2
    assert saved[0][1]["event_type"] == "trion_shell_checkpoint"
    assert saved[1][1]["event_type"] == "trion_shell_session_summary"
    assert saved[1][1]["event_data"]["raw_summary"] == "Service fixed"
