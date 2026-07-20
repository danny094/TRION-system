import json
from dataclasses import FrozenInstanceError

import pytest

from mcp.catalog_contracts import MCPDesiredState
from mcp.desired_state import (
    MCPRegistrySourceOutcome,
    MCPRegistrySourceStatus,
    compose_mcp_desired_state,
    load_registry_source,
)


def _core_defaults():
    return {"memory-mcp": {"enabled": True, "transport": "http"}}


class _StatBlindUnreadablePath:
    def __init__(self):
        self.exists_calls = 0
        self.read_calls = 0

    def exists(self):
        self.exists_calls += 1
        return False

    def read_text(self, *, encoding):
        assert encoding == "utf-8"
        self.read_calls += 1
        raise PermissionError("diagnostic detail is not authoritative")


def test_source_status_space_and_immutable_contract(tmp_path):
    assert {status.name for status in MCPRegistrySourceStatus} == {
        "MISSING",
        "READ_FAILED",
        "PARSE_FAILED",
        "VALID",
    }
    outcome = load_registry_source(tmp_path / "missing.json")
    assert outcome.status is MCPRegistrySourceStatus.MISSING
    assert outcome.custom_registry is None
    with pytest.raises(FrozenInstanceError):
        outcome.status = MCPRegistrySourceStatus.VALID

    desired = compose_mcp_desired_state(_core_defaults(), outcome)
    assert isinstance(desired, MCPDesiredState)
    assert set(desired.core_mcps) == {"memory-mcp"}
    assert dict(desired.custom_mcps) == {}
    with pytest.raises(FrozenInstanceError):
        desired.core_mcps = {}


def test_permission_failure_is_read_failed_without_exists_precheck():
    path = _StatBlindUnreadablePath()

    outcome = load_registry_source(path)

    assert path.exists_calls == 0
    assert path.read_calls == 1
    assert outcome.status is MCPRegistrySourceStatus.READ_FAILED
    with pytest.raises(ValueError):
        compose_mcp_desired_state(_core_defaults(), outcome)
    with pytest.raises(ValueError):
        compose_mcp_desired_state(
            _core_defaults(),
            MCPRegistrySourceOutcome(outcome.status, diagnostic="different detail"),
        )


def test_read_and_parse_failures_never_become_core_only_success(tmp_path):
    read_failure = load_registry_source(tmp_path)
    assert read_failure.status is MCPRegistrySourceStatus.READ_FAILED
    with pytest.raises(ValueError):
        compose_mcp_desired_state(_core_defaults(), read_failure)

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{not-json", encoding="utf-8")
    parse_failure = load_registry_source(invalid)
    assert parse_failure.status is MCPRegistrySourceStatus.PARSE_FAILED
    with pytest.raises(ValueError):
        compose_mcp_desired_state(_core_defaults(), parse_failure)

    invalid.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    assert load_registry_source(invalid).status is MCPRegistrySourceStatus.PARSE_FAILED


def test_valid_custom_data_stays_separate_and_collision_is_fail_closed(tmp_path):
    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps({"demo": {"enabled": True, "transport": "stdio"}}),
        encoding="utf-8",
    )
    outcome = load_registry_source(path)
    assert outcome == MCPRegistrySourceOutcome(
        status=MCPRegistrySourceStatus.VALID,
        custom_registry={"demo": {"enabled": True, "transport": "stdio"}},
        diagnostic=None,
    )
    desired = compose_mcp_desired_state(_core_defaults(), outcome)
    assert set(desired.core_mcps) == {"memory-mcp"}
    assert set(desired.custom_mcps) == {"demo"}
    assert "demo" not in desired.core_mcps

    collision = MCPRegistrySourceOutcome(
        status=MCPRegistrySourceStatus.VALID,
        custom_registry={"memory-mcp": {"enabled": False}},
    )
    with pytest.raises(ValueError):
        compose_mcp_desired_state(_core_defaults(), collision)


def test_source_outcome_requires_a_real_status_and_valid_status_payload_pair():
    with pytest.raises((TypeError, ValueError)):
        MCPRegistrySourceOutcome(status="MISSING")

    for status in MCPRegistrySourceStatus:
        if status is MCPRegistrySourceStatus.VALID:
            continue
        with pytest.raises(ValueError):
            MCPRegistrySourceOutcome(status=status, custom_registry={})

    empty = MCPRegistrySourceOutcome(
        status=MCPRegistrySourceStatus.VALID,
        custom_registry={},
    )
    assert dict(empty.custom_registry) == {}


@pytest.mark.parametrize(
    "custom_registry",
    [
        [],
        {1: {}},
        {"": {}},
        {"   ": {}},
        {"demo": []},
    ],
)
def test_source_outcome_rejects_malformed_direct_custom_registry(custom_registry):
    with pytest.raises((TypeError, ValueError)):
        MCPRegistrySourceOutcome(
            status=MCPRegistrySourceStatus.VALID,
            custom_registry=custom_registry,
        )


@pytest.mark.parametrize(
    ("core_mcps", "custom_mcps"),
    [
        ([], {}),
        ({}, []),
        ({1: {}}, {}),
        ({"": {}}, {}),
        ({"   ": {}}, {}),
        ({"memory-mcp": []}, {}),
        ({}, {1: {}}),
        ({}, {"demo": []}),
        ({"memory-mcp": {}}, {"memory-mcp": {}}),
    ],
)
def test_desired_state_rejects_malformed_direct_construction(core_mcps, custom_mcps):
    with pytest.raises((TypeError, ValueError)):
        MCPDesiredState(core_mcps=core_mcps, custom_mcps=custom_mcps)


def test_valid_contract_data_is_deeply_immutable_and_not_aliased():
    custom = {"demo": {"nested": {"flags": ["a"]}}}
    outcome = MCPRegistrySourceOutcome(
        status=MCPRegistrySourceStatus.VALID,
        custom_registry=custom,
    )
    custom["demo"]["nested"]["flags"].append("changed")
    assert outcome.custom_registry["demo"]["nested"]["flags"] == ("a",)
    with pytest.raises(TypeError):
        outcome.custom_registry["demo"]["nested"]["new"] = True

    core = {"memory-mcp": {"nested": {"flags": ["core"]}}}
    desired = MCPDesiredState(core_mcps=core, custom_mcps=outcome.custom_registry)
    core["memory-mcp"]["nested"]["flags"].append("changed")
    assert desired.core_mcps["memory-mcp"]["nested"]["flags"] == ("core",)
    with pytest.raises(TypeError):
        desired.core_mcps["memory-mcp"]["enabled"] = False
