from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class NetworkMode(str, Enum):
    NONE = "none"
    INTERNAL = "internal"
    BRIDGE = "bridge"
    FULL = "full"


class ResourceLimits(BaseModel):
    cpu_limit: str = Field(default="1.0")
    memory_limit: str = Field(default="512m")
    memory_swap: str = Field(default="1g")
    timeout_seconds: int = Field(default=300)
    pids_limit: int = Field(default=100)


class SessionQuota(BaseModel):
    max_containers: int = Field(default=2)
    max_total_memory_mb: int = Field(default=2048)
    max_total_cpu: float = Field(default=2.0)
    containers_used: int = 0
    memory_used_mb: int = 0
    cpu_used: float = 0.0
