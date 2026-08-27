import inspect

import container_commander_bundle_fakes  # noqa: F401
import bundle_docker  # noqa: E402
import bundle_dispatch  # noqa: E402
import bundle_exec  # noqa: E402
import bundle_network  # noqa: E402
import bundle_runtime_actions  # noqa: E402
import bundle_runtime_views  # noqa: E402


_CONTAINER_REFERENCE_TARGETS = (
    bundle_runtime_views.inspect_container,
    bundle_runtime_views.get_container_logs,
    bundle_runtime_views.get_container_stats,
    bundle_exec.container_exec,
    bundle_exec.container_exec_detailed,
    bundle_runtime_actions.remove_stopped_container,
    bundle_runtime_actions.start_stopped_container,
    bundle_runtime_actions.stop_container,
    bundle_network.get_network_info,
)


def test_generated_container_name_wrappers_have_compatible_targets():
    for target in _CONTAINER_REFERENCE_TARGETS:
        parameters = inspect.signature(target).parameters
        assert parameters["container_id"].default == ""
        assert parameters["container_name"].default == ""

        source = inspect.getsource(target)
        body = source.split("):", 1)[1]
        assert "container_name" not in body


def test_bundle_container_logs_resolves_name_and_rejects_ambiguous_reference(monkeypatch):
    class FakeContainer:
        id = "c1"
        name = "demo"

        def logs(self, **_kwargs):
            return b"hello\n"

    class FakeContainers:
        def get(self, container_ref):
            if container_ref in {"c1", "demo"}:
                return FakeContainer()
            raise KeyError(container_ref)

    client = type("FakeClient", (), {"containers": FakeContainers()})()
    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: client)

    result = bundle_dispatch.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "container_logs", "arguments": {"container_name": "demo"}},
    })
    assert result["result"]["structuredContent"]["container_id"] == "c1"
    assert result["result"]["structuredContent"]["logs"] == "hello\n"

    ambiguous = bundle_dispatch.handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "container_logs",
            "arguments": {"container_id": "c1", "container_name": "demo"},
        },
    })
    assert ambiguous["error"]["code"] == -32602


def test_bundle_results_preserve_normalized_short_container_id(monkeypatch):
    class FakeContainer:
        id = "full-container-id"
        attrs = {"NetworkSettings": {"Networks": {}}}

        def logs(self, **_kwargs):
            return b"hello\n"

        def stats(self, **_kwargs):
            return {}

    class FakeContainers:
        def get(self, container_ref):
            assert container_ref == "short-id"
            return FakeContainer()

    client = type("FakeClient", (), {"containers": FakeContainers()})()
    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: client)

    assert bundle_runtime_views.get_container_logs("short-id")["container_id"] == "short-id"
    assert bundle_runtime_views.get_container_stats("short-id")["container_id"] == "short-id"
    assert bundle_network.get_network_info("short-id")["container_id"] == "short-id"
