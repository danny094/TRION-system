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


class _BlueprintView:
    def __init__(self, blueprint_id: str, intents: list[dict]):
        self.id = blueprint_id
        self.hardware_intents = list(intents)


def test_hardware_routes_use_local_blueprint_loader(monkeypatch):
    hardware = _load_module("commander_api.hardware")
    monkeypatch.setattr(
        hardware,
        "load_blueprint_hardware_view",
        lambda blueprint_id, resolve=True: _BlueprintView(
            blueprint_id,
            [{"resource_id": "hw::device::/dev/dri/renderD128", "policy": {"container_path": "/dev/dri/renderD128"}}],
        ),
    )
    async def _fake_proxy(**kwargs):
        if kwargs["path"] == "/hardware/plan":
            return {"actions": [{"resource_id": "hw::device::/dev/dri/renderD128", "action": "attach"}]}
        if kwargs["path"] == "/hardware/validate":
            return {"issues": []}
        raise AssertionError(kwargs)

    monkeypatch.setattr(hardware, "proxy_runtime_hardware_request", _fake_proxy)
    async def _fake_preview(bp, connector="container", target_type="blueprint", target_id=""):
        return {
            "available": True,
            "connector": connector,
            "target_type": target_type,
            "target_id": target_id or bp.id,
            "summary": {"supported": True, "resolved_count": 1},
            "resolution": {},
        }

    monkeypatch.setattr(hardware, "build_blueprint_hardware_preview_payload", _fake_preview)

    payload = asyncio.run(hardware.get_blueprint_hardware_intents("bp1"))
    assert payload["blueprint_id"] == "bp1"
    assert payload["count"] == 1

    async def _plan():
        class _Request:
            async def body(self):
                return b'{"resolve": true}'

        return await hardware.plan_blueprint_hardware("bp1", _Request())

    planned = asyncio.run(_plan())
    assert planned["blueprint_id"] == "bp1"
    assert planned["plan"]["actions"][0]["resource_id"] == "hw::device::/dev/dri/renderD128"


def test_hardware_preview_uses_local_resolution_helper(monkeypatch):
    preview = _load_module("commander_api.hardware_preview")
    blueprint = _BlueprintView(
        "bp1",
        [{"resource_id": "hw::input::/dev/input/event0", "policy": {"container_path": "/dev/input/event0"}}],
    )

    async def _fake_proxy(**kwargs):
        if kwargs["path"] == "/hardware/plan":
            return {"actions": [{"resource_id": "hw::input::/dev/input/event0", "action": "attach"}]}
        if kwargs["path"] == "/hardware/validate":
            return {"issues": []}
        raise AssertionError(kwargs)

    monkeypatch.setattr(preview, "proxy_runtime_hardware_request", _fake_proxy)
    payload = asyncio.run(preview.build_blueprint_hardware_preview_payload(blueprint))
    assert payload["available"] is True
    assert payload["summary"]["resolved_count"] >= 1


def test_hardware_modules_no_longer_import_vendor_store_or_hardware():
    hardware_source = (ADMIN_API_DIR / "commander_api" / "hardware.py").read_text(encoding="utf-8")
    preview_source = (ADMIN_API_DIR / "commander_api" / "hardware_preview.py").read_text(encoding="utf-8")
    assert "from container_commander.store import resolve_blueprint" not in hardware_source
    assert "from container_commander.store import get_blueprint" not in hardware_source
    assert "from container_commander.hardware import" not in hardware_source
    assert "from container_commander.hardware import" not in preview_source


def test_deploy_hardware_module_resolves_with_local_truths(monkeypatch):
    deploy_hardware = _load_module("commander_deploy_hardware")

    calls = []

    def _fake_request_runtime_hardware(**kwargs):
        calls.append((kwargs["method"], kwargs["path"], dict(kwargs.get("json_body") or {})))
        if kwargs["path"] == "/hardware/plan":
            return {"actions": [{"resource_id": "hw::device::/dev/dri/renderD128", "action": "attach"}]}
        if kwargs["path"] == "/hardware/validate":
            return {"issues": []}
        raise AssertionError(kwargs)

    monkeypatch.setattr(deploy_hardware, "request_runtime_hardware", _fake_request_runtime_hardware)

    resolution = deploy_hardware.resolve_for_deploy(
        blueprint_id="bp1",
        intents=[{"resource_id": "hw::device::/dev/dri/renderD128", "policy": {"container_path": "/dev/dri/renderD128"}}],
    )

    assert resolution.blueprint_id == "bp1"
    assert resolution.resolved_count >= 1
    assert calls[0][1] == "/hardware/plan"
    assert calls[1][1] == "/hardware/validate"


def test_deploy_orchestrator_no_longer_imports_vendor_hardware():
    source = (ADMIN_API_DIR / "commander_deploy_orchestrator.py").read_text(encoding="utf-8")

    assert "from commander_deploy_hardware import (" in source
    assert "from commander_hardware_resolution import build_hardware_resolution_preview_payload" in source
    assert "from hardware import (" not in source
    assert "from hardware.block.preview import build_hardware_resolution_preview_payload" not in source
