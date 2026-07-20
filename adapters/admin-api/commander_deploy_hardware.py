from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Tuple

from commander_hardware_resolution import (
    HardwareResolution,
    build_hardware_resolution_preview_payload,
    intent_payloads,
    resolution_defaults,
    resolve_hardware_payloads,
)
from commander_runtime_hardware_client import (
    request_local_runtime_hardware_fallback,
    request_runtime_hardware,
    should_prefer_local_runtime_hardware,
)


logger = logging.getLogger(__name__)


def merge_device_overrides(explicit: Iterable[str] | None, resolved: Iterable[str] | None) -> List[str]:
    merged: List[str] = []
    seen: set[str] = set()
    for raw in list(explicit or []) + list(resolved or []):
        item = str(raw or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        merged.append(item)
    return merged


def merge_mount_overrides(
    explicit: Iterable[Dict[str, Any]] | None,
    resolved: Iterable[Dict[str, Any]] | None,
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str, str, str]] = set()
    for raw in list(explicit or []) + list(resolved or []):
        item = dict(raw or {})
        key = (
            str(item.get("asset_id") or "").strip(),
            str(item.get("host") or "").strip(),
            str(item.get("container") or "").strip(),
            str(item.get("mode") or "rw").strip().lower() or "rw",
        )
        if not key[2] or key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def build_warning_entries(resolution: HardwareResolution) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for raw in list(resolution.warnings or []):
        message = str(raw or "").strip()
        if not message or message in seen:
            continue
        seen.add(message)
        entries.append(
            {
                "name": "hardware_resolution",
                "detail": {
                    "message": message,
                    "connector": resolution.connector,
                    "target_type": resolution.target_type,
                    "target_id": resolution.target_id,
                },
            }
        )

    for resource_id in list(resolution.unresolved_resource_ids or []):
        item = str(resource_id or "").strip()
        if not item:
            continue
        message = f"unresolved_hardware_intent:{item}"
        if message in seen:
            continue
        seen.add(message)
        entries.append(
            {
                "name": "hardware_resolution",
                "detail": {
                    "message": message,
                    "resource_id": item,
                    "connector": resolution.connector,
                    "target_type": resolution.target_type,
                    "target_id": resolution.target_id,
                },
            }
        )

    for raw in list(resolution.block_apply_engine_handoffs or []):
        handoff = dict(raw or {})
        resource_id = str(handoff.get("resource_id") or "").strip()
        if not resource_id:
            continue
        message = f"disabled_block_engine_handoff_available:{resource_id}"
        if message in seen:
            continue
        seen.add(message)
        entries.append(
            {
                "name": "hardware_block_engine_handoff",
                "detail": {
                    "message": message,
                    "resource_id": resource_id,
                    "connector": resolution.connector,
                    "target_type": resolution.target_type,
                    "target_id": resolution.target_id,
                    "handoff": handoff,
                },
            }
        )

    return entries


@dataclass(slots=True)
class BlockEngineOptInDecision:
    requested_resource_ids: List[str] = field(default_factory=list)
    device_overrides: List[str] = field(default_factory=list)
    selected_resource_ids: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def select_block_engine_handoffs(
    handoffs: List[Dict[str, Any]] | None,
    requested_resource_ids: Iterable[Any] | None,
) -> BlockEngineOptInDecision:
    requested: List[str] = []
    seen_requested: set[str] = set()
    for raw in list(requested_resource_ids or []):
        item = str(raw or "").strip()
        if not item or item in seen_requested:
            continue
        seen_requested.add(item)
        requested.append(item)

    if not requested:
        return BlockEngineOptInDecision()

    handoff_index: Dict[str, Dict[str, Any]] = {}
    for raw in list(handoffs or []):
        handoff = dict(raw or {})
        resource_id = str(handoff.get("resource_id") or "").strip()
        if resource_id and resource_id not in handoff_index:
            handoff_index[resource_id] = handoff

    device_overrides: List[str] = []
    selected_resource_ids: List[str] = []
    warnings: List[str] = []
    seen_overrides: set[str] = set()

    for resource_id in requested:
        handoff = dict(handoff_index.get(resource_id) or {})
        if not handoff:
            warnings.append(f"block_engine_handoff_opt_in_unmatched:{resource_id}")
            continue
        selected_resource_ids.append(resource_id)
        warnings.append(f"block_engine_handoff_opt_in_applied:{resource_id}")
        for raw_override in list(handoff.get("device_overrides") or []):
            override = str(raw_override or "").strip()
            if not override or override in seen_overrides:
                continue
            seen_overrides.add(override)
            device_overrides.append(override)

    return BlockEngineOptInDecision(
        requested_resource_ids=requested,
        device_overrides=device_overrides,
        selected_resource_ids=selected_resource_ids,
        warnings=warnings,
    )


def resolve_for_deploy(
    *,
    blueprint_id: str,
    intents: Iterable[Any],
    connector: str = "container",
    target_type: str = "blueprint",
    target_id: str = "",
    timeout: float = 20.0,
) -> HardwareResolution:
    payloads = intent_payloads(intents)
    target_id_value = str(target_id or blueprint_id).strip() or str(blueprint_id or "").strip()
    if not payloads:
        return HardwareResolution(
            **resolution_defaults(
                blueprint_id=blueprint_id,
                connector=connector,
                target_type=target_type,
                target_id=target_id_value,
            )
        )

    plan_body = {
        "connector": connector,
        "target_type": target_type,
        "target_id": target_id_value,
        "intents": payloads,
    }
    validate_body = {
        "connector": connector,
        "target_type": target_type,
        "target_id": target_id_value,
        "resource_ids": [item.get("resource_id", "") for item in payloads if str(item.get("resource_id", "")).strip()],
    }

    if should_prefer_local_runtime_hardware():
        logger.info("[CommanderDeployHardware] Using local runtime-hardware for deploy resolution")
        try:
            plan_payload = request_local_runtime_hardware_fallback(path="/hardware/plan", json_body=plan_body)
            validate_payload = request_local_runtime_hardware_fallback(path="/hardware/validate", json_body=validate_body)
        except Exception as local_exc:
            return HardwareResolution(
                **resolution_defaults(
                    blueprint_id=blueprint_id,
                    connector=connector,
                    target_type=target_type,
                    target_id=target_id_value,
                ),
                warnings=[f"runtime_hardware_local_resolution_unavailable:{local_exc}"],
            )
    else:
        try:
            plan_payload = request_runtime_hardware(
                method="POST",
                path="/hardware/plan",
                json_body=plan_body,
                timeout=timeout,
            )
            validate_payload = request_runtime_hardware(
                method="POST",
                path="/hardware/validate",
                json_body=validate_body,
                timeout=timeout,
            )
        except Exception as exc:
            logger.warning("[CommanderDeployHardware] HTTP unavailable, trying local fallback: %s", exc)
            try:
                plan_payload = request_local_runtime_hardware_fallback(path="/hardware/plan", json_body=plan_body)
                validate_payload = request_local_runtime_hardware_fallback(path="/hardware/validate", json_body=validate_body)
                logger.info("[CommanderDeployHardware] Using local runtime-hardware fallback")
            except Exception as local_exc:
                return HardwareResolution(
                    **resolution_defaults(
                        blueprint_id=blueprint_id,
                        connector=connector,
                        target_type=target_type,
                        target_id=target_id_value,
                    ),
                    warnings=[
                        f"runtime_hardware_resolution_unavailable:{exc}",
                        f"runtime_hardware_local_resolution_unavailable:{local_exc}",
                    ],
                )
    return resolve_hardware_payloads(
        blueprint_id=blueprint_id,
        intents=payloads,
        plan_payload=dict(plan_payload or {}),
        validate_payload=dict(validate_payload or {}),
        connector=connector,
        target_type=target_type,
        target_id=target_id_value,
    )
