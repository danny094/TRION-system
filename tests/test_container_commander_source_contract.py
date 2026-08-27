import inspect

import pytest

from container_commander_v2_fakes import _FakeClient, _FakeContainer
from tools_network import network_info
from tools_runtime import container_exec, container_exec_detailed, container_inspect, container_logs, container_stats
from tools_runtime_actions import remove_stopped_container, start_stopped_container, stop_container
from runtime_views import get_container_stats

from container_reference import ContainerReferenceError, resolve_container_reference  # noqa: E402


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"container_id": "c1"}, "c1"),
        ({"container_name": "demo"}, "c1"),
    ],
)
def test_resolve_container_reference_accepts_exactly_one_identifier(kwargs, expected):
    container = _FakeContainer(cid="c1", name="demo")
    resolved = resolve_container_reference(_FakeClient(container), **kwargs)
    assert resolved.id == expected


@pytest.mark.parametrize(
    "kwargs",
    [
        {"container_id": "c1", "container_name": "demo"},
        {},
    ],
)
def test_resolve_container_reference_rejects_both_or_neither(kwargs):
    with pytest.raises(ContainerReferenceError):
        resolve_container_reference(_FakeClient(_FakeContainer()), **kwargs)


@pytest.mark.parametrize(
    "tool_fn",
    [
        container_inspect,
        container_logs,
        container_stats,
        container_exec,
        container_exec_detailed,
        start_stopped_container,
        stop_container,
        remove_stopped_container,
        network_info,
    ],
)
def test_public_tool_contracts_expose_optional_container_name(tool_fn):
    signature = inspect.signature(tool_fn)
    assert "container_id" in signature.parameters
    assert "container_name" in signature.parameters
    assert signature.parameters["container_name"].default == ""


def test_runtime_views_resolve_container_name_to_real_container_id(monkeypatch):
    container = _FakeContainer(cid="c1", name="demo", status="running")
    monkeypatch.setattr("runtime_views._client", lambda: _FakeClient(container))

    result = get_container_stats(container_name="demo")

    assert result["container_id"] == "c1"
