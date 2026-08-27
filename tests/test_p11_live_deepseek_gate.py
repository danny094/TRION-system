from __future__ import annotations

from inspect import signature

import pytest

from tests import p11_live_http
from tests import test_deepseek_backend_live as live


def _responses(*, keys=None, effective=None, catalog=None):
    role_values = {
        "THINKING_PROVIDER": "deepseek",
        "CONTROL_PROVIDER": "deepseek",
        "OUTPUT_PROVIDER": "deepseek",
        "OUTPUT_MODEL": "deepseek-v4-flash",
    }
    role_values.update(effective or {})
    catalog_values = {
        "OUTPUT_PROVIDER": role_values["OUTPUT_PROVIDER"],
        "OUTPUT_MODEL": role_values["OUTPUT_MODEL"],
    }
    catalog_values.update(catalog or {})
    return {
        "/health": {"status": "ok"},
        "/api/settings/api-keys": {
            "keys": [{"id": "DEEPSEEK_API_KEY"}] if keys is None else keys,
        },
        "/api/models/catalog": {"effective": catalog_values},
        "/api/settings/models/effective": {"effective": role_values},
    }


def test_deepseek_opt_in_skips_before_http(monkeypatch):
    monkeypatch.delenv("TRION_ENABLE_DEEPSEEK_TESTS", raising=False)

    def unexpected_request(*args, **kwargs):
        raise AssertionError("HTTP must not run without explicit process opt-in")

    monkeypatch.setattr(live, "get_json", unexpected_request)

    with pytest.raises(pytest.skip.Exception):
        live.require_deepseek_backend()


def test_deepseek_gate_reads_effective_role_endpoint(monkeypatch):
    monkeypatch.setenv("TRION_ENABLE_DEEPSEEK_TESTS", "1")
    responses = _responses()
    seen = []

    def get_json(path, **kwargs):
        seen.append(path)
        return responses[path]

    monkeypatch.setattr(live, "get_json", get_json)

    result = live.require_deepseek_backend()

    assert "/api/settings/models/effective" in seen
    assert result["model"] == "deepseek-v4-flash"


@pytest.mark.parametrize(
    "role",
    ("THINKING_PROVIDER", "CONTROL_PROVIDER", "OUTPUT_PROVIDER"),
)
def test_deepseek_role_mismatch_blocks_before_chat(monkeypatch, role):
    monkeypatch.setenv("TRION_ENABLE_DEEPSEEK_TESTS", "1")
    responses = _responses(effective={role: "minimax"})
    monkeypatch.setattr(live, "get_json", lambda path, **kwargs: responses[path])

    with pytest.raises(AssertionError, match=role):
        live.require_deepseek_backend()


def test_deepseek_missing_key_blocks_before_chat(monkeypatch):
    monkeypatch.setenv("TRION_ENABLE_DEEPSEEK_TESTS", "1")
    responses = _responses(keys=[])
    monkeypatch.setattr(live, "get_json", lambda path, **kwargs: responses[path])

    with pytest.raises(AssertionError, match="key missing"):
        live.require_deepseek_backend()


def test_deepseek_missing_model_blocks_before_chat(monkeypatch):
    monkeypatch.setenv("TRION_ENABLE_DEEPSEEK_TESTS", "1")
    responses = _responses(effective={"OUTPUT_MODEL": ""}, catalog={"OUTPUT_MODEL": ""})
    monkeypatch.setattr(live, "get_json", lambda path, **kwargs: responses[path])

    with pytest.raises(AssertionError, match="OUTPUT_MODEL"):
        live.require_deepseek_backend()


def test_live_http_helper_is_transport_only():
    assert not hasattr(p11_live_http, "assert_no_ollama_fallback")
    assert len(signature(p11_live_http.post_chat_events).parameters) <= 5
