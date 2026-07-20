"""Shared runtime quota compatibility helpers."""

from __future__ import annotations

from commander_deploy_runtime_state import (
    RuntimeStateRefs,
    commit_quota_reservation,
    parse_memory,
    release_quota_reservation,
    reserve_quota,
    update_quota_used_unlocked,
)


def get_quota(state: RuntimeStateRefs):
    return state.quota.model_copy(deep=True)


def check_quota(resources, state: RuntimeStateRefs) -> None:
    mem_mb, cpu = reserve_quota(resources, state)
    release_quota_reservation(mem_mb, cpu, state)
