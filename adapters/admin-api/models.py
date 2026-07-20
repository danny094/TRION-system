"""
Admin-API Commander models.

This is the local truth for the shared commander schema used by localized
Admin-API modules. The legacy vendor path re-exports from here for
compatibility during migration.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NetworkMode(str, Enum):
    NONE = "none"
    INTERNAL = "internal"
    BRIDGE = "bridge"
    FULL = "full"


class ContainerStatus(str, Enum):
    READY = "ready"
    BUILDING = "building"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class SecretScope(str, Enum):
    GLOBAL = "global"
    BLUEPRINT = "blueprint"


class ResourceLimits(BaseModel):
    cpu_limit: str = Field(default="1.0", description="CPU cores (e.g. '0.5', '2.0')")
    memory_limit: str = Field(default="512m", description="RAM limit (e.g. '256m', '2g')")
    memory_swap: str = Field(default="1g", description="Swap limit")
    timeout_seconds: int = Field(default=300, description="Auto-kill TTL in seconds")
    pids_limit: int = Field(default=100, description="Max processes inside container")


class MountDef(BaseModel):
    host: str = Field(..., description="Host path (relative to project root)")
    container: str = Field(..., description="Container mount path")
    type: str = Field(default="bind", description="Mount type: bind or volume")
    mode: str = Field(default="rw", description="ro or rw")
    asset_id: Optional[str] = Field(
        default=None,
        description="Optional published storage asset id backing this mount",
    )


class PreStartExec(BaseModel):
    user: str = Field(default="", description="User inside the helper container")
    command: str = Field(default="", description="Shell command executed before launch")


class StorageAsset(BaseModel):
    id: str = Field(..., description="Stable asset identifier")
    label: str = Field(default="", description="Display label shown in pickers")
    path: str = Field(..., description="Absolute host path")
    zone: str = Field(default="managed_services", description="Storage Broker zone")
    policy_state: str = Field(default="managed_rw", description="Storage Broker policy state")
    published_to_commander: bool = Field(default=False, description="Whether the asset is selectable in Commander")
    default_mode: str = Field(default="ro", description="Default mount mode: ro or rw")
    allowed_for: List[str] = Field(
        default_factory=list,
        description="Intended usage hints (appdata/media/backup/workspace/games)",
    )
    source_disk_id: Optional[str] = Field(default=None, description="Originating disk or partition id")
    source_kind: str = Field(default="manual", description="manual | service_dir | existing_path | import")
    notes: str = Field(default="", description="Operator notes")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class HardwareIntent(BaseModel):
    resource_id: str = Field(..., description="Stable hardware resource identifier")
    target_type: str = Field(default="container", description="Intended runtime target type")
    target_id: str = Field(default="", description="Optional target identifier placeholder")
    attachment_mode: str = Field(default="attach", description="Desired action such as attach/detach")
    policy: Dict[str, Any] = Field(default_factory=dict, description="Connector-specific desired policy")
    requested_by: str = Field(default="", description="Optional actor/source marker")


class SecretRequirement(BaseModel):
    name: str = Field(..., description="Environment variable name (e.g. OPENAI_API_KEY)")
    description: str = Field(default="", description="What this secret is used for")
    optional: bool = Field(default=False, description="Container can run without it")


class SecretEntry(BaseModel):
    id: Optional[int] = None
    name: str
    scope: SecretScope = SecretScope.GLOBAL
    blueprint_id: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None


class SecretRef(BaseModel):
    name: str
    scope: str
    blueprint_id: Optional[str] = None
    exists: bool = True


class Blueprint(BaseModel):
    id: str = Field(..., description="Unique identifier (e.g. 'python-sandbox')")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="What this blueprint is for")
    extends: Optional[str] = Field(default=None, description="Parent blueprint ID for inheritance")
    dockerfile: str = Field(default="", description="Dockerfile content or path")
    image: Optional[str] = Field(default=None, description="Pre-built image (alternative to dockerfile)")
    image_digest: Optional[str] = Field(
        default=None,
        description=(
            "Optional pinned image digest (sha256:...) for trust verification. "
            "If set: start_container() fails if resolved digest doesn't match (fail closed). "
            "If None: start allowed with warning (opt-in, backwards compatible)."
        ),
    )
    system_prompt: str = Field(default="", description="System prompt for KI when using this container")
    resources: ResourceLimits = Field(default_factory=ResourceLimits)
    secrets_required: List[SecretRequirement] = Field(default_factory=list)
    mounts: List[MountDef] = Field(default_factory=list)
    storage_scope: str = Field(
        default="",
        description="Optional approved storage scope name for host bind mounts.",
    )
    ports: List[str] = Field(
        default_factory=list,
        description="Port mappings (e.g. ['47984:47984/tcp', '48100-48110:48100-48110/udp'])",
    )
    runtime: str = Field(default="", description="Container runtime (e.g. 'nvidia')")
    devices: List[str] = Field(
        default_factory=list,
        description="Host devices passed through to container (e.g. ['/dev/dri:/dev/dri'])",
    )
    hardware_intents: List[HardwareIntent] = Field(
        default_factory=list,
        description="Structured desired hardware/resource attachments resolved later via runtime-hardware.",
    )
    environment: Dict[str, str] = Field(default_factory=dict, description="Static environment variables (non-secret).")
    healthcheck: Dict[str, Any] = Field(
        default_factory=dict,
        description="Docker healthcheck configuration (test/interval/timeout/retries/start_period).",
    )
    pre_start_exec: Optional[PreStartExec] = Field(
        default=None,
        description="Optional pre-start hook executed in a short-lived helper container before launch.",
    )
    cap_add: List[str] = Field(default_factory=list, description="Additional Linux capabilities (e.g. ['NET_ADMIN']).")
    security_opt: List[str] = Field(
        default_factory=list,
        description="Docker security options (e.g. ['seccomp=unconfined']).",
    )
    cap_drop: List[str] = Field(
        default_factory=list,
        description="Linux capabilities to drop explicitly (e.g. ['NET_RAW']).",
    )
    privileged: bool = Field(default=False, description="Run container in privileged mode. High risk; requires approval.")
    read_only_rootfs: bool = Field(default=False, description="Run container with a read-only root filesystem.")
    shm_size: str = Field(default="", description="Shared memory size (e.g. '1g').")
    ipc_mode: str = Field(default="", description="Docker IPC mode (e.g. 'host').")
    network: NetworkMode = Field(default=NetworkMode.INTERNAL)
    allowed_exec: List[str] = Field(
        default_factory=list,
        description=(
            "Allowlist of permitted command prefixes for exec_in_container. "
            "Empty = no restriction. E.g. ['python', 'pip', 'sh']"
        ),
    )
    tags: List[str] = Field(default_factory=list)
    icon: str = Field(default="📦", description="Emoji icon for UI")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ContainerInstance(BaseModel):
    container_id: str
    blueprint_id: str
    name: str
    status: ContainerStatus = ContainerStatus.READY
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_limit_mb: float = 512.0
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0
    started_at: Optional[str] = None
    runtime_seconds: int = 0
    ttl_remaining: int = 0
    efficiency_score: float = 1.0
    efficiency_level: str = "green"
    volume_name: Optional[str] = None
    has_snapshot: bool = False
    cpu_limit_alloc: float = 1.0
    network_info: Dict = Field(default_factory=dict)
    session_id: str = ""
    deploy_warnings: List[Dict] = Field(default_factory=list)
    hardware_resolution_preview: Dict[str, Any] = Field(default_factory=dict)
    block_apply_handoff_resource_ids_requested: List[str] = Field(default_factory=list)
    block_apply_handoff_resource_ids_applied: List[str] = Field(default_factory=list)


class SessionQuota(BaseModel):
    max_containers: int = Field(default=2, description="Max simultaneous containers")
    max_total_memory_mb: int = Field(default=2048, description="Total RAM budget")
    max_total_cpu: float = Field(default=2.0, description="Total CPU budget")
    containers_used: int = 0
    memory_used_mb: int = 0
    cpu_used: float = 0.0


class DeployRequest(BaseModel):
    blueprint_id: str
    override_resources: Optional[ResourceLimits] = None
    environment: Dict[str, str] = Field(default_factory=dict)


class ExecRequest(BaseModel):
    container_id: str
    command: str
    timeout: int = Field(default=30, description="Exec timeout in seconds")


class BlueprintCreateRequest(BaseModel):
    id: str
    name: str
    description: str = ""
    dockerfile: str = ""
    image: Optional[str] = None
    system_prompt: str = ""
    resources: Optional[ResourceLimits] = None
    secrets_required: List[SecretRequirement] = Field(default_factory=list)
    mounts: List[MountDef] = Field(default_factory=list)
    storage_scope: str = ""
    ports: List[str] = Field(default_factory=list)
    runtime: str = ""
    devices: List[str] = Field(default_factory=list)
    hardware_intents: List[HardwareIntent] = Field(default_factory=list)
    environment: Dict[str, str] = Field(default_factory=dict)
    healthcheck: Dict[str, Any] = Field(default_factory=dict)
    cap_add: List[str] = Field(default_factory=list)
    security_opt: List[str] = Field(default_factory=list)
    cap_drop: List[str] = Field(default_factory=list)
    privileged: bool = False
    read_only_rootfs: bool = False
    shm_size: str = ""
    ipc_mode: str = ""
    network: NetworkMode = NetworkMode.INTERNAL
    tags: List[str] = Field(default_factory=list)
    icon: str = "📦"
    extends: Optional[str] = None


class SecretStoreRequest(BaseModel):
    name: str
    value: str

