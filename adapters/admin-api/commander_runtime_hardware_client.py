from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import httpx

from utils.routing.service_endpoint import candidate_service_endpoints


logger = logging.getLogger(__name__)

_DEFAULT_CONNECTOR = "container"
_DEFAULT_TARGET_TYPE = "blueprint"
_DEFAULT_TIMEOUT = 20.0


def runtime_hardware_base_urls() -> list[str]:
    return candidate_service_endpoints(
        configured=(os.environ.get("RUNTIME_HARDWARE_URL") or "").strip(),
        port=8420,
        scheme="http",
        service_name=os.environ.get("RUNTIME_HARDWARE_SERVICE_NAME", "").strip(),
        prefer_container_service=True,
        include_gateway=True,
        include_host_docker=True,
        include_loopback=True,
        include_localhost=True,
    )


def request_runtime_hardware(
    *,
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> Any:
    last_error: Exception | None = None
    for base_url in runtime_hardware_base_urls():
        url = f"{base_url}{path}"
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers={"Accept": "application/json"},
                )
            content_type = response.headers.get("content-type", "")
            payload: Any
            if "application/json" in content_type:
                payload = response.json()
            else:
                payload = {"ok": response.is_success, "text": response.text}
            if response.status_code >= 400:
                raise RuntimeError(f"runtime_hardware_http_{response.status_code}:{payload}")
            return payload
        except Exception as exc:
            last_error = exc
            logger.warning("[CommanderRuntimeHardwareClient] %s %s failed via %s: %s", method, path, base_url, exc)
            continue
    raise RuntimeError(f"runtime_hardware_unreachable:{last_error}" if last_error else "runtime_hardware_unreachable")


def runtime_hardware_support_dir() -> str:
    root = Path(__file__).resolve().parents[2]
    support_dir = root / "adapters" / "runtime-hardware"
    if support_dir.is_dir():
        return str(support_dir)
    app_support_dir = Path("/app/adapters/runtime-hardware")
    if app_support_dir.is_dir():
        return str(app_support_dir)
    return ""


def runtime_hardware_has_host_visibility() -> bool:
    return (
        Path("/host_proc").exists()
        and Path("/run/udev/data").exists()
        and any(Path(candidate).exists() for candidate in ("/dev/dri", "/dev/input", "/dev/uinput", "/dev/vfio/vfio"))
    )


def should_prefer_local_runtime_hardware() -> bool:
    forced = str(os.environ.get("RUNTIME_HARDWARE_LOCAL_FIRST") or "").strip().lower()
    if forced in {"1", "true", "yes", "on"}:
        return True
    if forced in {"0", "false", "no", "off"}:
        return False
    return Path("/app/adapters/runtime-hardware").is_dir() and runtime_hardware_has_host_visibility()


def _load_runtime_hardware_package(support_dir: str) -> None:
    package_dir = Path(support_dir) / "runtime_hardware"
    init_path = package_dir / "__init__.py"
    if not init_path.is_file():
        raise RuntimeError("runtime_hardware_local_package_missing")

    existing = sys.modules.get("runtime_hardware")
    if existing is not None and str(getattr(existing, "__file__", "") or "") == str(init_path):
        return

    spec = importlib.util.spec_from_file_location(
        "runtime_hardware",
        init_path,
        submodule_search_locations=[str(package_dir)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("runtime_hardware_local_package_spec_failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules["runtime_hardware"] = module
    spec.loader.exec_module(module)


def request_local_runtime_hardware_fallback(*, path: str, json_body: dict[str, Any]) -> dict[str, Any]:
    support_dir = runtime_hardware_support_dir()
    if not support_dir:
        raise RuntimeError("runtime_hardware_local_support_unavailable")

    try:
        _load_runtime_hardware_package(support_dir)
        _connectors = importlib.import_module("runtime_hardware.connectors")
        _models = importlib.import_module("runtime_hardware.models")
        ContainerConnector = _connectors.ContainerConnector
        _container_storage_discovery = _connectors.container_storage_discovery
        AttachmentIntent = _models.AttachmentIntent
    except Exception as exc:
        raise RuntimeError(f"runtime_hardware_local_import_failed:{exc}") from exc

    connector_name = str(json_body.get("connector") or _DEFAULT_CONNECTOR).strip() or _DEFAULT_CONNECTOR
    if connector_name != "container":
        raise RuntimeError(f"runtime_hardware_local_connector_unsupported:{connector_name}")

    def _storage_broker_disks(timeout: float = 8.0) -> dict[str, Any]:
        broker_url = str(os.environ.get("STORAGE_BROKER_URL") or "http://storage-broker:8089").strip().rstrip("/")
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "storage_list_disks", "arguments": {}},
            "id": 1,
        }
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{broker_url}/mcp",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "mcp-session-id": "runtime-hardware-local-fallback",
                },
            )
        if response.status_code not in (200, 202):
            raise RuntimeError(f"storage_broker_http_{response.status_code}")
        for line in response.text.splitlines():
            if not line.startswith("data:"):
                continue
            envelope = json.loads(line[5:].strip())
            result = envelope.get("result", {})
            content = list(result.get("content") or [])
            if content:
                return dict(json.loads(content[0].get("text", "{}")) or {})
            return dict(result or {})
        return {}

    def _local_admin(path_value: str, params: dict[str, Any] | None = None, timeout: float = 8.0) -> dict[str, Any]:
        normalized = str(path_value or "").strip()
        if normalized == "/api/storage-broker/disks":
            return _storage_broker_disks(timeout=timeout)
        if normalized == "/api/commander/storage/assets":
            from commander_storage_assets_store import list_assets

            published_only = str((params or {}).get("published_only") or "").strip().lower() == "true"
            return {"assets": list_assets(published_only=published_only)}
        raise RuntimeError(f"runtime_hardware_local_admin_equivalent_unsupported:{normalized}")

    connector = ContainerConnector()
    original_fetch = _container_storage_discovery._fetch_admin_api_json
    _container_storage_discovery._fetch_admin_api_json = _local_admin
    try:
        if path == "/hardware/plan":
            intents = [AttachmentIntent.model_validate(item) for item in list(json_body.get("intents") or [])]
            plan_obj = connector.plan(
                target_type=str(json_body.get("target_type") or _DEFAULT_TARGET_TYPE).strip() or _DEFAULT_TARGET_TYPE,
                target_id=str(json_body.get("target_id") or "").strip(),
                intents=intents,
            )
            return dict(plan_obj.model_dump())
        if path == "/hardware/validate":
            validate_obj = connector.validate(
                target_type=str(json_body.get("target_type") or _DEFAULT_TARGET_TYPE).strip() or _DEFAULT_TARGET_TYPE,
                target_id=str(json_body.get("target_id") or "").strip(),
                resource_ids=list(json_body.get("resource_ids") or []),
            )
            return dict(validate_obj.model_dump())
        raise RuntimeError(f"runtime_hardware_local_path_unsupported:{path}")
    finally:
        _container_storage_discovery._fetch_admin_api_json = original_fetch
