"""Shared exec policy compatibility helpers."""

from __future__ import annotations


class PolicyViolationError(Exception):
    def __init__(self, command: str, allowed: list, blueprint_id: str):
        self.command = command
        self.allowed = allowed
        self.blueprint_id = blueprint_id
        super().__init__(
            f"policy_denied: '{command.split()[0] if command else '?'}' not in allowed_exec "
            f"for '{blueprint_id}'. Allowed: {allowed}"
        )
