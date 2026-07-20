from __future__ import annotations

from typing import Any, Dict, FrozenSet, Optional, Tuple


class CronParseError(ValueError):
    pass


class CronPolicyError(ValueError):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        status_code: int = 409,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.error_code = str(error_code or "cron_policy_violation")
        self.status_code = int(status_code)
        self.details = details or {}


_TRION_OBJECTIVE_ALLOWED_HINTS: Tuple[str, ...] = (
    "status", "health", "summary", "digest", "report", "sync",
    "cleanup", "maint", "monitor", "backup", "index", "archive",
    "memory", "recall", "plan", "review", "check",
)

_TRION_OBJECTIVE_RISKY_HINTS: Tuple[str, ...] = (
    "delete", "drop", "truncate", "remove", "destroy", "wipe",
    "shutdown", "reboot", "restart", "kill", "secret", "password",
    "token", "api key", "credential", "docker", "network",
    "firewall", "sudo", "chmod", "chown", "rm -rf",
)

# Risky keywords that are pre-approved when a compatible allowed hint is present.
# Truly dangerous keywords (wipe, truncate, drop, sudo, chmod, chown,
# secret, password, token, credential) are never context-approved.
_TRION_RISKY_CONTEXT_APPROVED: Dict[str, FrozenSet[str]] = {
    "delete":   frozenset({"cleanup", "maint", "archive", "backup", "index", "digest"}),
    "remove":   frozenset({"cleanup", "maint", "archive", "backup"}),
    "restart":  frozenset({"health", "monitor", "maint", "check", "status"}),
    "kill":     frozenset({"health", "monitor", "maint", "check", "status"}),
    "docker":   frozenset({"status", "health", "monitor", "cleanup", "backup", "maint", "check", "sync"}),
    "network":  frozenset({"status", "health", "monitor", "check", "report"}),
    "shutdown": frozenset({"maint", "backup", "plan"}),
    "reboot":   frozenset({"maint", "health", "check", "plan"}),
    "firewall": frozenset({"status", "health", "monitor", "check", "report"}),
}

_TRION_OBJECTIVE_HARD_BLOCK_HINTS: Tuple[str, ...] = (
    "rm -rf", "mkfs", "dd if=", "poweroff", ":(){:|:&};:",
)
