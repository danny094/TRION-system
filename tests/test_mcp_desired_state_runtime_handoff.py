import json

import pytest


def test_runtime_handoff_uses_one_source_and_one_composer(monkeypatch, tmp_path):
    import mcp.config as config

    calls = {"defaults": 0, "source": 0, "compose": 0}
    original_source = config.load_registry_source
    original_compose = config.compose_mcp_desired_state
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"custom": {"enabled": True}}), encoding="utf-8")
    monkeypatch.setattr(config, "_CONFIG_PATH", path)
    monkeypatch.setattr(config, "_default_mcps", lambda: calls.__setitem__("defaults", calls["defaults"] + 1) or {"core": {"enabled": True}})

    def source(registry_path, *, core_ids):
        calls["source"] += 1
        assert registry_path == path
        assert core_ids == {"core"}
        return original_source(registry_path, core_ids=core_ids)

    def compose(defaults, outcome):
        calls["compose"] += 1
        return original_compose(defaults, outcome)

    monkeypatch.setattr(config, "load_registry_source", source)
    monkeypatch.setattr(config, "compose_mcp_desired_state", compose)

    desired = config.get_mcp_desired_state()

    assert set(desired.core_mcps) == {"core"}
    assert set(desired.custom_mcps) == {"custom"}
    assert calls == {"defaults": 1, "source": 1, "compose": 1}


def test_legacy_registry_projection_does_not_reconstruct_core(monkeypatch):
    import mcp.config as config

    desired = config.MCPDesiredState(
        core_mcps={"memory-mcp": {"enabled": True, "tool_intents": {"tools": [{"name": "x"}]}}},
        custom_mcps={"custom": {"enabled": False}},
    )
    monkeypatch.setattr(config, "get_mcp_desired_state", lambda: desired)
    monkeypatch.setattr(config, "_default_mcps", lambda: pytest.fail("second core read"))

    payload = config._load_registry()

    assert payload["memory-mcp"]["tool_intents"]["tools"][0]["name"] == "x"
    assert payload["custom"]["enabled"] is False


def test_source_failure_is_not_swallowed(monkeypatch, tmp_path):
    import mcp.config as config

    monkeypatch.setattr(config, "_CONFIG_PATH", tmp_path)
    monkeypatch.setattr(config, "_default_mcps", lambda: {"core": {"enabled": True}})

    with pytest.raises(ValueError):
        config.get_mcp_desired_state()
