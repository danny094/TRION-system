from __future__ import annotations

import logging
import posixpath
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Tuple

from pydantic import BaseModel, Field

from commander_storage_assets_store import get_asset


logger = logging.getLogger(__name__)

_DEFAULT_CONNECTOR = "container"
_DEFAULT_TARGET_TYPE = "blueprint"
_RESOLVABLE_DEVICE_KINDS = {"device", "input", "usb"}
_BLOCKED_CONTAINER_TARGETS = {
    "/", "/boot", "/dev", "/etc", "/proc", "/run", "/sys", "/usr", "/var/run", "/workspace",
}
_BLOCKED_CONTAINER_TARGET_PREFIXES = (
    "/boot/", "/dev/", "/etc/", "/proc/", "/run/", "/sys/", "/usr/", "/var/run/", "/workspace/",
)


class HardwareResolution(BaseModel):
    blueprint_id: str
    connector: str = "container"
    target_type: str = "blueprint"
    target_id: str = ""
    supported: bool = False
    resolved_count: int = 0
    requires_restart: bool = False
    requires_approval: bool = False
    device_overrides: List[str] = Field(default_factory=list)
    mount_overrides: List[Dict[str, Any]] = Field(default_factory=list)
    block_device_refs: List[str] = Field(default_factory=list)
    block_apply_previews: List[Dict[str, Any]] = Field(default_factory=list)
    block_apply_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    block_apply_container_plans: List[Dict[str, Any]] = Field(default_factory=list)
    block_apply_engine_handoffs: List[Dict[str, Any]] = Field(default_factory=list)
    mount_refs: List[str] = Field(default_factory=list)
    stage_only_resource_ids: List[str] = Field(default_factory=list)
    unresolved_resource_ids: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


def resolution_defaults(
    *,
    blueprint_id: str,
    connector: str = _DEFAULT_CONNECTOR,
    target_type: str = _DEFAULT_TARGET_TYPE,
    target_id: str = "",
) -> Dict[str, Any]:
    return {
        "blueprint_id": str(blueprint_id or "").strip(),
        "connector": str(connector or _DEFAULT_CONNECTOR).strip() or _DEFAULT_CONNECTOR,
        "target_type": str(target_type or _DEFAULT_TARGET_TYPE).strip() or _DEFAULT_TARGET_TYPE,
        "target_id": str(target_id or blueprint_id).strip() or str(blueprint_id or "").strip(),
    }


def empty_hardware_resolution(
    *,
    blueprint_id: str,
    connector: str = _DEFAULT_CONNECTOR,
    target_type: str = _DEFAULT_TARGET_TYPE,
    target_id: str = "",
    warnings: Iterable[str] | None = None,
) -> HardwareResolution:
    resolution = HardwareResolution(
        **resolution_defaults(
            blueprint_id=blueprint_id,
            connector=connector,
            target_type=target_type,
            target_id=target_id,
        )
    )
    for raw in list(warnings or []):
        warning = str(raw or "").strip()
        if warning:
            resolution.warnings.append(warning)
    return resolution


def _resource_ids(items: Iterable[Dict[str, Any]] | None) -> List[str]:
    values: List[str] = []
    seen: set[str] = set()
    for raw in list(items or []):
        item = dict(raw or {})
        resource_id = str(item.get("resource_id") or "").strip()
        if not resource_id or resource_id in seen:
            continue
        seen.add(resource_id)
        values.append(resource_id)
    return values


def build_hardware_resolution_preview_payload(resolution: Any) -> Dict[str, Any]:
    model_dump = getattr(resolution, "model_dump", None)
    payload = dict(model_dump() if callable(model_dump) else dict(resolution or {}))

    block_candidate_resource_ids = _resource_ids(payload.get("block_apply_candidates"))
    container_plan_resource_ids = _resource_ids(payload.get("block_apply_container_plans"))
    engine_handoff_resource_ids = _resource_ids(payload.get("block_apply_engine_handoffs"))

    return {
        "supported": bool(payload.get("supported")),
        "resolved_count": int(payload.get("resolved_count") or 0),
        "requires_restart": bool(payload.get("requires_restart")),
        "requires_approval": bool(payload.get("requires_approval")),
        "device_override_count": len(list(payload.get("device_overrides") or [])),
        "mount_override_count": len(list(payload.get("mount_overrides") or [])),
        "block_candidate_resource_ids": block_candidate_resource_ids,
        "container_plan_resource_ids": container_plan_resource_ids,
        "engine_handoff_resource_ids": engine_handoff_resource_ids,
        "block_apply_handoff_resource_ids_hint": list(engine_handoff_resource_ids),
        "engine_opt_in_available": bool(engine_handoff_resource_ids),
        "unresolved_resource_ids": [str(item or "").strip() for item in list(payload.get("unresolved_resource_ids") or []) if str(item or "").strip()],
        "warnings": [str(item or "").strip() for item in list(payload.get("warnings") or []) if str(item or "").strip()],
    }


def intent_payloads(intents: Iterable[Any]) -> List[Dict[str, Any]]:
    payloads: List[Dict[str, Any]] = []
    for raw in list(intents or []):
        if isinstance(raw, dict):
            payloads.append(dict(raw))
            continue
        model_dump = getattr(raw, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump()
            if isinstance(dumped, dict):
                payloads.append(dict(dumped))
    return payloads


def parse_resource_id(resource_id: str) -> Tuple[str, str]:
    parts = str(resource_id or "").strip().split("::", 2)
    if len(parts) != 3:
        return "", ""
    return parts[1].strip(), parts[2].strip()


def _validate_issue_index(validate_payload: Dict[str, Any]) -> Dict[str, List[str]]:
    issue_index: Dict[str, List[str]] = {}
    for raw in list((validate_payload or {}).get("issues") or []):
        issue = str(raw or "").strip()
        if not issue:
            continue
        matched = False
        for prefix in ("resource_not_found:", "unsupported_resource_kind:"):
            if issue.startswith(prefix):
                issue_index.setdefault(issue.split(":", 1)[1].strip(), []).append(issue)
                matched = True
                break
        if not matched:
            issue_index.setdefault("_global", []).append(issue)
    return issue_index


@dataclass(slots=True)
class BlockApplyPreviewDecision:
    previews: List[Dict[str, Any]] = field(default_factory=list)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_container_device_path(raw_path: Any) -> str:
    path = str(raw_path or "").strip()
    if not path or not path.startswith("/dev/") or ".." in path or any(ch.isspace() for ch in path):
        return ""
    return path


def build_block_apply_preview(
    *,
    resource_id: str,
    action_metadata: Dict[str, Any] | None = None,
    policy: Dict[str, Any] | None = None,
    unresolved: bool = False,
    warnings: List[str] | None = None,
) -> BlockApplyPreviewDecision:
    metadata = dict(action_metadata or {})
    resource_metadata = dict(metadata.get("resource_metadata") or {})
    host_path = str(metadata.get("host_path") or "").strip()
    requested_mode = _normalize_text((policy or {}).get("mode")) or "ro"
    disk_type = _normalize_text(resource_metadata.get("disk_type")) or "unknown"
    zone = _normalize_text(resource_metadata.get("zone")) or "unzoned"
    policy_state = _normalize_text(resource_metadata.get("policy_state")) or "unknown"
    raw_requested_runtime_path = (policy or {}).get("runtime_path") or (policy or {}).get("container_path") or (policy or {}).get("device_path")
    requested_runtime_path = _normalize_container_device_path(raw_requested_runtime_path)
    explicit_runtime_path_invalid = bool(str(raw_requested_runtime_path or "").strip()) and not requested_runtime_path
    target_runtime_path = requested_runtime_path or host_path
    allowed_operations = [
        _normalize_text(item)
        for item in list(resource_metadata.get("allowed_operations") or [])
        if _normalize_text(item)
    ]

    reason = "review_only"
    eligible = False
    apply_mode = "review_only"
    blockers: List[str] = []

    if unresolved:
        reason = "policy_blocked"
        blockers.append("policy_blocked")
    elif disk_type != "part":
        reason = "whole_disk_or_unknown_review_only"
        blockers.append("whole_disk_or_unknown_review_only")
    elif requested_mode not in {"ro", "rw"}:
        reason = "invalid_requested_mode"
        blockers.append("invalid_requested_mode")
    elif policy_state not in {"managed_rw", "read_only"}:
        reason = "unsupported_policy_state"
        blockers.append("unsupported_policy_state")
    elif requested_mode == "rw" and policy_state != "managed_rw":
        reason = "write_not_permitted"
        blockers.append("write_not_permitted")
    elif allowed_operations and "assign_to_container" not in allowed_operations:
        reason = "operation_not_allowed"
        blockers.append("operation_not_allowed")
    elif not host_path.startswith("/dev/"):
        reason = "invalid_host_path"
        blockers.append("invalid_host_path")
    elif explicit_runtime_path_invalid:
        reason = "invalid_container_device_path"
        blockers.append("invalid_container_device_path")
        target_runtime_path = ""
    elif not target_runtime_path:
        reason = "invalid_container_device_path"
        blockers.append("invalid_container_device_path")
    else:
        eligible = True
        apply_mode = "stage_device_passthrough_candidate"
        reason = "candidate_for_explicit_container_apply"

    candidate_device_override = ""
    if host_path.startswith("/dev/") and target_runtime_path:
        candidate_device_override = host_path if target_runtime_path == host_path else f"{host_path}:{target_runtime_path}"

    requirements = [
        "explicit_user_approval",
        "container_recreate_required",
        "future_engine_block_apply_enablement",
    ]
    if requested_mode == "rw":
        requirements.append("write_access_review")
    if eligible:
        requirements.append("device_path_must_remain_visible_on_host")

    preview = {
        "resource_id": str(resource_id or "").strip(),
        "host_path": host_path,
        "disk_type": disk_type,
        "zone": zone,
        "policy_state": policy_state,
        "requested_mode": requested_mode,
        "target_runtime": "container",
        "target_runtime_path": target_runtime_path,
        "candidate_runtime_binding": {
            "kind": "device_path",
            "source_path": host_path,
            "target_path": target_runtime_path,
            "binding_expression": candidate_device_override,
        },
        "apply_strategy": "runtime_device_binding",
        "allowed_operations": allowed_operations,
        "eligible": eligible,
        "apply_mode": apply_mode,
        "reason": reason,
        "requirements": requirements,
        "blockers": blockers,
        "requires_restart": True,
        "requires_approval": True,
        "warnings": [str(item or "").strip() for item in list(warnings or []) if str(item or "").strip()],
        "runtime_parameters": {
            "container": {
                "candidate_container_path": target_runtime_path,
                "candidate_device_override": candidate_device_override,
                "device_override_mode": "docker_devices",
            }
        },
    }
    return BlockApplyPreviewDecision(previews=[preview] if preview["resource_id"] else [])


@dataclass(slots=True)
class BlockApplyCandidateDecision:
    candidates: List[Dict[str, Any]] = field(default_factory=list)


def build_block_apply_candidates(previews: List[Dict[str, Any]] | None) -> BlockApplyCandidateDecision:
    candidates: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for raw in list(previews or []):
        preview = dict(raw or {})
        if not bool(preview.get("eligible")):
            continue
        resource_id = str(preview.get("resource_id") or "").strip()
        host_path = str(preview.get("host_path") or "").strip()
        runtime_target = str(preview.get("target_runtime") or "").strip() or "container"
        runtime_path = str(preview.get("target_runtime_path") or "").strip()
        runtime_binding = dict(preview.get("candidate_runtime_binding") or {})
        binding_expression = str(runtime_binding.get("binding_expression") or "").strip()
        if not resource_id or not binding_expression or not runtime_path or not host_path or resource_id in seen:
            continue
        seen.add(resource_id)
        candidates.append(
            {
                "resource_id": resource_id,
                "host_path": host_path,
                "target_runtime": runtime_target,
                "target_runtime_path": runtime_path,
                "runtime_binding": {
                    "kind": str(runtime_binding.get("kind") or "device_path").strip() or "device_path",
                    "source_path": str(runtime_binding.get("source_path") or host_path).strip() or host_path,
                    "target_path": str(runtime_binding.get("target_path") or runtime_path).strip() or runtime_path,
                    "binding_expression": binding_expression,
                },
                "requested_mode": str(preview.get("requested_mode") or "").strip() or "ro",
                "apply_strategy": str(preview.get("apply_strategy") or "runtime_device_binding").strip(),
                "activation_state": "disabled_until_engine_support",
                "activation_reason": "future_engine_block_apply_enablement",
                "requires_restart": bool(preview.get("requires_restart")),
                "requires_approval": bool(preview.get("requires_approval")),
                "requirements": [str(item or "").strip() for item in list(preview.get("requirements") or []) if str(item or "").strip()],
                "warnings": [str(item or "").strip() for item in list(preview.get("warnings") or []) if str(item or "").strip()],
                "runtime_parameters": dict(preview.get("runtime_parameters") or {}),
            }
        )
    return BlockApplyCandidateDecision(candidates=candidates)


@dataclass(slots=True)
class ContainerBlockAdapterDecision:
    plans: List[Dict[str, Any]] = field(default_factory=list)


def build_container_block_apply_adapter_plan(candidates: List[Dict[str, Any]] | None) -> ContainerBlockAdapterDecision:
    plans: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for raw in list(candidates or []):
        candidate = dict(raw or {})
        resource_id = str(candidate.get("resource_id") or "").strip()
        target_runtime = str(candidate.get("target_runtime") or "").strip()
        runtime_binding = dict(candidate.get("runtime_binding") or {})
        binding_expression = str(runtime_binding.get("binding_expression") or "").strip()
        runtime_parameters = dict(candidate.get("runtime_parameters") or {})
        container_params = dict(runtime_parameters.get("container") or {})
        candidate_device_override = str(container_params.get("candidate_device_override") or "").strip()
        candidate_container_path = str(container_params.get("candidate_container_path") or "").strip()
        if not resource_id or resource_id in seen:
            continue
        seen.add(resource_id)
        if target_runtime != "container" or not binding_expression or not candidate_device_override or not candidate_container_path:
            continue
        plans.append(
            {
                "resource_id": resource_id,
                "target_runtime": "container",
                "adapter_state": "disabled_until_engine_support",
                "adapter_reason": "future_engine_block_apply_enablement",
                "device_overrides": [candidate_device_override],
                "container_path": candidate_container_path,
                "runtime_binding": {
                    "kind": str(runtime_binding.get("kind") or "device_path").strip() or "device_path",
                    "source_path": str(runtime_binding.get("source_path") or "").strip(),
                    "target_path": str(runtime_binding.get("target_path") or "").strip(),
                    "binding_expression": binding_expression,
                },
                "requirements": [str(item or "").strip() for item in list(candidate.get("requirements") or []) if str(item or "").strip()],
                "warnings": [str(item or "").strip() for item in list(candidate.get("warnings") or []) if str(item or "").strip()],
            }
        )
    return ContainerBlockAdapterDecision(plans=plans)


@dataclass(slots=True)
class BlockEngineHandoffDecision:
    handoffs: List[Dict[str, Any]] = field(default_factory=list)


def build_disabled_container_block_engine_handoffs(plans: List[Dict[str, Any]] | None) -> BlockEngineHandoffDecision:
    handoffs: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for raw in list(plans or []):
        plan = dict(raw or {})
        resource_id = str(plan.get("resource_id") or "").strip()
        target_runtime = str(plan.get("target_runtime") or "").strip()
        container_path = str(plan.get("container_path") or "").strip()
        device_overrides = [str(item or "").strip() for item in list(plan.get("device_overrides") or []) if str(item or "").strip()]
        runtime_binding = dict(plan.get("runtime_binding") or {})
        binding_expression = str(runtime_binding.get("binding_expression") or "").strip()
        if not resource_id or resource_id in seen:
            continue
        seen.add(resource_id)
        if target_runtime != "container" or not container_path or not device_overrides or not binding_expression:
            continue
        handoffs.append(
            {
                "resource_id": resource_id,
                "target_runtime": "container",
                "engine_handoff_state": "disabled_until_engine_support",
                "engine_handoff_reason": "explicit_engine_opt_in_required",
                "engine_target": "start_container",
                "device_overrides": list(device_overrides),
                "container_path": container_path,
                "runtime_binding": {
                    "kind": str(runtime_binding.get("kind") or "device_path").strip() or "device_path",
                    "source_path": str(runtime_binding.get("source_path") or "").strip(),
                    "target_path": str(runtime_binding.get("target_path") or "").strip(),
                    "binding_expression": binding_expression,
                },
                "requirements": [str(item or "").strip() for item in list(plan.get("requirements") or []) if str(item or "").strip()],
                "warnings": [str(item or "").strip() for item in list(plan.get("warnings") or []) if str(item or "").strip()],
            }
        )
    return BlockEngineHandoffDecision(handoffs=handoffs)


@dataclass(slots=True)
class BlockDeviceResolutionDecision:
    block_device_refs: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    unresolved_resource_ids: List[str] = field(default_factory=list)


def resolve_block_device_ref(
    *,
    resource_id: str,
    action: Dict[str, Any] | None = None,
    action_metadata: Dict[str, Any] | None = None,
    policy: Dict[str, Any] | None = None,
) -> BlockDeviceResolutionDecision:
    resource_key = str(resource_id or "").strip()
    if not resource_key:
        return BlockDeviceResolutionDecision()

    metadata = dict(action_metadata or {})
    resource_metadata = dict(metadata.get("resource_metadata") or {})
    requested_mode = str((policy or {}).get("mode") or "").strip().lower()
    policy_state = _normalize_text(resource_metadata.get("policy_state"))
    zone = _normalize_text(resource_metadata.get("zone"))
    disk_type = _normalize_text(resource_metadata.get("disk_type"))
    allowed_operations = {_normalize_text(item) for item in list(resource_metadata.get("allowed_operations") or []) if _normalize_text(item)}
    host_path = str(metadata.get("host_path") or "").strip()
    is_system = bool(resource_metadata.get("is_system")) or zone == "system"

    if host_path and not host_path.startswith("/dev/"):
        return BlockDeviceResolutionDecision(
            warnings=[f"invalid_block_device_host_path:{resource_key}"],
            unresolved_resource_ids=[resource_key],
        )
    if is_system:
        return BlockDeviceResolutionDecision(
            warnings=[f"system_block_device_ref_forbidden:{resource_key}"],
            unresolved_resource_ids=[resource_key],
        )
    if policy_state == "blocked":
        return BlockDeviceResolutionDecision(
            warnings=[f"storage_broker_policy_blocked:{resource_key}"],
            unresolved_resource_ids=[resource_key],
        )
    if requested_mode == "rw" and policy_state == "read_only":
        return BlockDeviceResolutionDecision(
            warnings=[f"storage_broker_policy_read_only:{resource_key}"],
            unresolved_resource_ids=[resource_key],
        )
    if allowed_operations and "assign_to_container" not in allowed_operations:
        return BlockDeviceResolutionDecision(
            warnings=[f"storage_broker_operation_not_allowed:{resource_key}"],
            unresolved_resource_ids=[resource_key],
        )

    decision = BlockDeviceResolutionDecision(
        block_device_refs=[resource_key],
        warnings=[f"storage_review_required:{resource_key}"],
    )
    if disk_type == "disk":
        decision.warnings.append(f"whole_disk_review_required:{resource_key}")
    if requested_mode == "rw":
        decision.warnings.append(f"block_device_write_review_required:{resource_key}")

    explanation = str(((action or {}).get("explanation")) or "").strip()
    if explanation and explanation.startswith(("storage_", "block_device_")):
        decision.warnings.append(explanation)
    return decision


def _input_mount_override_for_host_path(host_path: str) -> Dict[str, Any]:
    normalized = str(host_path or "").strip()
    if normalized.startswith("/dev/input/"):
        normalized = "/dev/input"
    return {"host": normalized or "/dev/input", "container": "/dev/input", "type": "bind", "mode": "rw"}


def _normalize_container_target_path(raw_path: str) -> str:
    path = str(raw_path or "").strip()
    if not path or not path.startswith("/"):
        return ""
    normalized = posixpath.normpath(path)
    return normalized if normalized.startswith("/") else ""


def _is_blocked_container_target(path: str) -> bool:
    normalized = _normalize_container_target_path(path)
    if not normalized:
        return True
    if normalized in _BLOCKED_CONTAINER_TARGETS:
        return True
    return any(normalized.startswith(prefix) for prefix in _BLOCKED_CONTAINER_TARGET_PREFIXES)


def materialize_mount_ref_overrides(
    *,
    resolution: HardwareResolution,
    intents: List[Dict[str, Any]],
) -> HardwareResolution:
    if not list(resolution.mount_refs or []):
        return resolution

    intent_by_resource = {
        str(item.get("resource_id") or "").strip(): item
        for item in list(intents or {})
        if str(item.get("resource_id") or "").strip()
    }
    updated = resolution.model_copy(deep=True)
    kept_warnings: List[str] = []
    resolved_mounts: set[str] = set()
    explicit_mount_targets: set[str] = set()
    new_unresolved: set[str] = set(updated.unresolved_resource_ids or [])

    for resource_id in list(updated.mount_refs or []):
        resource_key = str(resource_id or "").strip()
        kind, asset_id = parse_resource_id(resource_key)
        if kind != "mount_ref" or not asset_id:
            new_unresolved.add(resource_key)
            updated.warnings.append(f"invalid_mount_ref:{resource_key}")
            continue

        intent = dict(intent_by_resource.get(resource_key) or {})
        policy = dict(intent.get("policy") or {})
        container_path = _normalize_container_target_path(str(policy.get("container_path") or policy.get("container") or "").strip())
        if not container_path:
            kept_warnings.append(f"storage_broker_materialization_required:{resource_key}")
            continue
        explicit_mount_targets.add(resource_key)
        if _is_blocked_container_target(container_path):
            new_unresolved.add(resource_key)
            updated.warnings.append(f"blocked_mount_ref_target:{resource_key}:{container_path}")
            continue

        asset = get_asset(asset_id)
        if not asset:
            new_unresolved.add(resource_key)
            updated.warnings.append(f"storage_asset_not_found:{asset_id}")
            continue
        if not bool((asset or {}).get("published_to_commander")):
            new_unresolved.add(resource_key)
            updated.warnings.append(f"storage_asset_not_published:{asset_id}")
            continue

        policy_state = str((asset or {}).get("policy_state", "managed_rw") or "managed_rw").strip().lower()
        if policy_state not in {"blocked", "read_only", "managed_rw"}:
            policy_state = "managed_rw"
        if policy_state == "blocked":
            new_unresolved.add(resource_key)
            updated.warnings.append(f"storage_asset_policy_blocked:{asset_id}")
            continue

        asset_mode = str((asset or {}).get("default_mode", "ro") or "ro").strip().lower()
        if asset_mode not in {"ro", "rw"}:
            asset_mode = "ro"
        mode = str(policy.get("mode") or "").strip().lower() or asset_mode
        if mode not in {"ro", "rw"}:
            new_unresolved.add(resource_key)
            updated.warnings.append(f"invalid_mount_ref_mode:{resource_key}")
            continue
        if policy_state == "read_only" and mode == "rw":
            new_unresolved.add(resource_key)
            updated.warnings.append(f"storage_asset_policy_read_only:{asset_id}")
            continue
        if asset_mode == "ro" and mode == "rw":
            new_unresolved.add(resource_key)
            updated.warnings.append(f"storage_asset_read_only:{asset_id}")
            continue

        override = {"asset_id": asset_id, "container": container_path, "type": "bind", "mode": mode}
        if override not in updated.mount_overrides:
            updated.mount_overrides.append(override)
        resolved_mounts.add(resource_key)

    seen_warnings: set[str] = set()
    deduped: List[str] = []
    for raw in list(updated.warnings or []):
        warning = str(raw or "").strip()
        if not warning or warning in seen_warnings:
            continue
        if warning.startswith("storage_broker_materialization_required:"):
            key = warning.split(":", 1)[1].strip()
            if key in resolved_mounts or key in explicit_mount_targets:
                continue
        seen_warnings.add(warning)
        deduped.append(warning)
    for warning in kept_warnings:
        if warning and warning not in seen_warnings:
            seen_warnings.add(warning)
            deduped.append(warning)
    updated.warnings = deduped
    updated.unresolved_resource_ids = [item for item in list(updated.unresolved_resource_ids or []) if item not in resolved_mounts]
    for item in sorted(new_unresolved):
        if item and item not in updated.unresolved_resource_ids:
            updated.unresolved_resource_ids.append(item)
    updated.supported = (
        bool(updated.device_overrides or updated.mount_overrides or updated.block_device_refs or updated.mount_refs)
        and not updated.unresolved_resource_ids
    )
    return updated


def resolve_hardware_payloads(
    *,
    blueprint_id: str,
    intents: Iterable[Any],
    plan_payload: dict,
    validate_payload: dict,
    connector: str = _DEFAULT_CONNECTOR,
    target_type: str = _DEFAULT_TARGET_TYPE,
    target_id: str = "",
) -> HardwareResolution:
    payloads = intent_payloads(intents)
    actions = list((plan_payload or {}).get("actions") or [])
    action_by_resource = {
        str(item.get("resource_id") or "").strip(): item
        for item in actions
        if str(item.get("resource_id") or "").strip()
    }
    issue_index = _validate_issue_index(validate_payload or {})
    resolution = HardwareResolution(
        **resolution_defaults(
            blueprint_id=blueprint_id,
            connector=connector,
            target_type=target_type,
            target_id=target_id,
        )
    )

    seen_device: set[str] = set()
    seen_stage: set[str] = set()
    seen_unresolved: set[str] = set()
    seen_warnings: set[str] = set()
    seen_block_refs: set[str] = set()
    seen_mount_refs: set[str] = set()

    for intent in list(payloads or []):
        resource_id = str((intent or {}).get("resource_id") or "").strip()
        if not resource_id:
            continue
        action = action_by_resource.get(resource_id) or {}
        action_kind = str(action.get("action") or "").strip()
        kind, host_path = parse_resource_id(resource_id)
        issues = list(issue_index.get(resource_id) or [])

        if issues:
            for issue in issues:
                if issue not in seen_warnings:
                    resolution.warnings.append(issue)
                    seen_warnings.add(issue)
            if resource_id not in seen_unresolved:
                resolution.unresolved_resource_ids.append(resource_id)
                seen_unresolved.add(resource_id)
            continue

        if action_kind in {"unsupported", "reject"} or not host_path or not kind:
            if resource_id not in seen_unresolved:
                resolution.unresolved_resource_ids.append(resource_id)
                seen_unresolved.add(resource_id)
            explanation = str(action.get("explanation") or "").strip()
            if explanation and explanation not in seen_warnings:
                resolution.warnings.append(explanation)
                seen_warnings.add(explanation)
            continue

        if bool(action.get("requires_restart")):
            resolution.requires_restart = True
        if bool(action.get("requires_approval")):
            resolution.requires_approval = True
        if action_kind == "stage_for_recreate" and resource_id not in seen_stage:
            resolution.stage_only_resource_ids.append(resource_id)
            seen_stage.add(resource_id)

        policy = dict((intent or {}).get("policy") or {})
        if kind == "input" and action_kind != "stage_for_recreate":
            override = _input_mount_override_for_host_path(host_path)
            if override not in resolution.mount_overrides:
                resolution.mount_overrides.append(override)
                resolution.resolved_count += 1
            continue

        if kind in _RESOLVABLE_DEVICE_KINDS:
            container_path = str(policy.get("container_path") or host_path).strip() or host_path
            if not container_path.startswith("/"):
                container_path = host_path
            device_override = host_path if container_path == host_path else f"{host_path}:{container_path}"
            if device_override not in seen_device:
                resolution.device_overrides.append(device_override)
                seen_device.add(device_override)
                resolution.resolved_count += 1
            continue

        if kind == "block_device_ref":
            decision = resolve_block_device_ref(
                resource_id=resource_id,
                action=action,
                action_metadata=dict(action.get("metadata") or {}),
                policy=policy,
            )
            for item in list(decision.block_device_refs or []):
                if item and item not in seen_block_refs:
                    resolution.block_device_refs.append(item)
                    seen_block_refs.add(item)
                    resolution.resolved_count += 1
            for warning in list(decision.warnings or []):
                text = str(warning or "").strip()
                if text and text not in seen_warnings:
                    resolution.warnings.append(text)
                    seen_warnings.add(text)
            for item in list(decision.unresolved_resource_ids or []):
                if item and item not in seen_unresolved:
                    resolution.unresolved_resource_ids.append(item)
                    seen_unresolved.add(item)
            preview = build_block_apply_preview(
                resource_id=resource_id,
                action_metadata=dict(action.get("metadata") or {}),
                policy=policy,
                unresolved=bool(decision.unresolved_resource_ids),
                warnings=list(decision.warnings or []),
            )
            for payload in list(preview.previews or []):
                if payload and payload not in resolution.block_apply_previews:
                    resolution.block_apply_previews.append(dict(payload))
            candidates = build_block_apply_candidates(list(preview.previews or []))
            for candidate in list(candidates.candidates or []):
                if candidate and candidate not in resolution.block_apply_candidates:
                    resolution.block_apply_candidates.append(dict(candidate))
            adapter = build_container_block_apply_adapter_plan(list(candidates.candidates or []))
            for plan in list(adapter.plans or []):
                if plan and plan not in resolution.block_apply_container_plans:
                    resolution.block_apply_container_plans.append(dict(plan))
            handoffs = build_disabled_container_block_engine_handoffs(list(adapter.plans or []))
            for handoff in list(handoffs.handoffs or []):
                if handoff and handoff not in resolution.block_apply_engine_handoffs:
                    resolution.block_apply_engine_handoffs.append(dict(handoff))
            continue

        if kind == "mount_ref":
            if resource_id not in seen_mount_refs:
                resolution.mount_refs.append(resource_id)
                seen_mount_refs.add(resource_id)
                resolution.resolved_count += 1
            warning = f"storage_broker_materialization_required:{resource_id}"
            if warning not in seen_warnings:
                resolution.warnings.append(warning)
                seen_warnings.add(warning)
            continue

        if resource_id not in seen_unresolved:
            resolution.unresolved_resource_ids.append(resource_id)
            seen_unresolved.add(resource_id)

    resolution.supported = bool(payloads) and not bool(resolution.unresolved_resource_ids)
    return materialize_mount_ref_overrides(resolution=resolution, intents=payloads)
