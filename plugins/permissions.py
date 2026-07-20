from typing import Any

from mcp.installer_common import InstallationError
from plugins.contracts import PLUGIN_PERMISSION_KEYS


def normalize_permissions(value: Any) -> dict[str, list[str]]:
    if value is None:
        return _empty_permissions()
    if not isinstance(value, dict):
        raise InstallationError("permissions must be an object")
    permissions = _empty_permissions()
    for key in PLUGIN_PERMISSION_KEYS:
        permissions[key] = _string_list(value.get(key), key)
    return permissions


def is_api_allowed(manifest: dict[str, Any], path: str) -> bool:
    return _matches_rule(path, manifest.get("permissions", {}).get("api", []))


def is_tool_allowed(manifest: dict[str, Any], tool_name: str) -> bool:
    return _matches_rule(tool_name, manifest.get("permissions", {}).get("tools", []))


def _empty_permissions() -> dict[str, list[str]]:
    return {key: [] for key in PLUGIN_PERMISSION_KEYS}


def _string_list(value: Any, key: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise InstallationError(f"permissions.{key} must be a list")
    return [str(item).strip() for item in value if str(item).strip()]


def _matches_rule(value: str, rules: list[str]) -> bool:
    candidate = str(value).strip()
    if not candidate:
        return False
    for rule in rules:
        if rule.endswith("*") and candidate.startswith(rule[:-1]):
            return True
        if candidate == rule:
            return True
    return False
