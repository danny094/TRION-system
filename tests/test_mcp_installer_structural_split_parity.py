"""Parity guards for the installer registry-validation and health splits."""

import asyncio

import pytest

import mcp.config as mcp_config
import mcp.installer_common as installer_common
import mcp.installer_health as installer_health
import mcp.installer_registry as installer_registry
import mcp.installer_registry_validation as registry_validation
from mcp.installer_common import InstallationError


class _FakeHub:
    def __init__(self, payload=None, error=None):
        self._payload = payload
        self._error = error

    def list_mcps(self):
        if self._error is not None:
            raise self._error
        return self._payload


def _run_health_check(monkeypatch, hub):
    async def _fail_if_called(*_args, **_kwargs):
        raise AssertionError("delay path must not run with attempts=1")

    monkeypatch.setattr(installer_health.asyncio, "sleep", _fail_if_called)
    return asyncio.run(
        installer_health.run_post_install_health_check(
            hub,
            "demo",
            attempts=1,
        )
    )


def test_registry_facades_are_exact_split_functions_and_constant_is_single_owned():
    assert (
        installer_registry._assert_mirror_consistency
        is registry_validation._assert_mirror_consistency
    )
    assert (
        installer_registry._assert_mirror_hash_matches_projection
        is registry_validation._assert_mirror_hash_matches_projection
    )
    assert not hasattr(installer_registry, "_PROJECTED_TOOL_FIELDS")
    assert registry_validation._PROJECTED_TOOL_FIELDS == (
        "tool_intent_meta",
        "capability_complete",
        "missing_capability_fields",
    )


def test_mirror_guard_blocks_before_registry_write(monkeypatch, tmp_path):
    registry_path = tmp_path / "mcp_registry.json"
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", registry_path)
    writes = []
    monkeypatch.setattr(installer_registry, "_write_registry", writes.append)
    inconsistent_config = {
        "version": "1.0.0",
        "tool_intents": {
            "schema_version": 1,
            "source_sha256": "not-authoritative-here",
            "bundle_version": "2.0.0",
            "tools": [],
        },
    }

    with pytest.raises(InstallationError):
        installer_registry.upsert_registry_entry("demo", inconsistent_config)

    assert writes == []
    assert not registry_path.exists()


def test_health_facades_are_exact_split_functions():
    assert installer_common.is_online_flag is installer_health.is_online_flag
    assert (
        installer_common.run_post_install_health_check
        is installer_health.run_post_install_health_check
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        ({"online": True}, True),
        ({"online": False}, False),
        ({"ok": True}, True),
        ({"status": "healthy"}, True),
        ({"status": "online"}, True),
        ({"status": "ready"}, True),
        ({"status": "offline"}, False),
        ({"status": "unknown"}, False),
    ],
)
def test_is_online_flag_preserves_existing_projection(value, expected):
    assert installer_health.is_online_flag(value) is expected


def test_health_check_without_callable_list_mcps_is_unknown(monkeypatch):
    result = _run_health_check(monkeypatch, object())

    assert result == {"status": "unknown", "reason": "hub_missing_list_mcps"}


def test_health_check_with_invalid_payload_is_unknown(monkeypatch):
    result = _run_health_check(monkeypatch, _FakeHub(payload={"demo": True}))

    assert result == {"status": "unknown", "reason": "invalid_list_mcps_payload"}


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ([{"name": "demo", "online": True}], {"status": "healthy", "reason": "online"}),
        (
            [{"name": "demo", "online": False}],
            {"status": "unhealthy", "reason": "mcp_listed_offline"},
        ),
        ([{"name": "other", "online": True}], {"status": "unhealthy", "reason": "mcp_not_listed"}),
    ],
)
def test_health_check_preserves_controlled_outcomes(monkeypatch, payload, expected):
    assert _run_health_check(monkeypatch, _FakeHub(payload=payload)) == expected


def test_health_check_list_failure_is_controlled_unhealthy(monkeypatch):
    result = _run_health_check(monkeypatch, _FakeHub(error=RuntimeError("opaque detail")))

    assert result["status"] == "unhealthy"
    assert result["reason"].partition(":")[0] == "list_mcps_error"
