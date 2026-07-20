"""Validation of installer-owned tool-intent registry projections."""

from typing import Any, Dict

from mcp.installer_common import InstallationError
from mcp.installer_tool_intents import canonical_json_sha256, project_tool

_PROJECTED_TOOL_FIELDS = (
    "tool_intent_meta",
    "capability_complete",
    "missing_capability_fields",
)


def _assert_mirror_consistency(config: Dict[str, Any]) -> None:
    """Validate a non-empty mirror before the registry write."""
    mirror = config.get("tool_intents")
    if not isinstance(mirror, dict) or not mirror:
        return
    manifest_version = str(config.get("version", "") or "").strip()
    mirror_version = str(mirror.get("bundle_version", "") or "").strip()
    if mirror_version != manifest_version:
        raise InstallationError(
            f"tool_intents mirror bundle_version {mirror_version!r} does not "
            f"match manifest version {manifest_version!r}"
        )
    header = {
        "schema_version": mirror.get("schema_version"),
        "source_sha256": mirror.get("source_sha256"),
        "bundle_version": mirror.get("bundle_version"),
    }
    for tool in mirror.get("tools", []):
        if tool.get("tool_intent_meta") != header:
            raise InstallationError(
                f"tool_intent_meta for tool {tool.get('name')!r} does not "
                "match the mirror header"
            )
    _assert_mirror_hash_matches_projection(mirror)


def _assert_mirror_hash_matches_projection(mirror: Dict[str, Any]) -> None:
    """Recompute hash input and denormalized capability markers."""
    actual_tools = mirror.get("tools", [])
    schema_version = mirror.get("schema_version")
    reconstructed_tools = [
        {key: value for key, value in tool.items() if key not in _PROJECTED_TOOL_FIELDS}
        for tool in actual_tools
    ]
    reconstructed = {"schema_version": schema_version, "tools": reconstructed_tools}
    if canonical_json_sha256(reconstructed) != mirror.get("source_sha256"):
        raise InstallationError(
            "tool_intents mirror source_sha256 does not match its tool "
            "projection (tool content was modified after the mirror was built)"
        )
    meta = {
        "schema_version": schema_version,
        "source_sha256": mirror.get("source_sha256"),
        "bundle_version": mirror.get("bundle_version"),
    }
    expected_tools = [project_tool(tool, schema_version, meta) for tool in reconstructed_tools]
    if expected_tools != actual_tools:
        raise InstallationError(
            "tool_intents mirror tool projection does not match the recomputed "
            "projection (capability_complete/missing_capability_fields drift)"
        )
