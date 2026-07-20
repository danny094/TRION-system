import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest
from core.output.stream import complete_output
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _load_models_routes():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    spec = importlib.util.spec_from_file_location(
        "trion_models_routes_for_p1_tests",
        ADMIN_API_DIR / "models_routes.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _json_response_payload(response):
    return json.loads(response.body.decode("utf-8"))


def test_models_catalog_returns_provider_aware_selected_model(monkeypatch):
    models_routes = _load_models_routes()

    from utils.settings import settings as runtime_settings

    monkeypatch.setattr(
        runtime_settings,
        "settings",
        {"OUTPUT_MODEL": "gpt-4.1-mini", "OUTPUT_PROVIDER": "openai"},
    )

    async def fake_fetch_tags(endpoint, headers=None):
        if headers:
            return [{"name": "llama3.3", "size": 123}]
        return [{"name": "local-model", "size": 456}]

    async def fake_resolve_key(provider):
        # W1/SP4.1: models_catalog() ruft den Resolver jetzt fuer mehrere
        # Cloud-Provider auf (ollama_cloud, openrouter, minimax), nicht mehr
        # nur fuer ollama_cloud. Fake muss alle drei beantworten koennen.
        assert provider in {"ollama_cloud", "openrouter", "minimax"}
        return "cloud-key" if provider == "ollama_cloud" else ""

    monkeypatch.setattr(models_routes, "_fetch_tags", fake_fetch_tags)
    monkeypatch.setattr("core.llm_provider_client._resolve_cloud_api_key", fake_resolve_key)

    response = asyncio.run(models_routes.models_catalog())
    payload = _json_response_payload(response)

    # W1/SP4.1: provider_ids() liefert inzwischen auch openrouter/minimax
    # (core/llm/provider_registry.py PROVIDER_SPECS), Test stammte aus der
    # Zeit vor deren Einfuehrung.
    assert payload["providers"] == ["ollama", "ollama_cloud", "openai", "anthropic", "openrouter", "minimax"]
    assert payload["effective"] == {
        "OUTPUT_MODEL": "gpt-4.1-mini",
        "OUTPUT_PROVIDER": "openai",
    }

    selected = [row for row in payload["models"] if row["selected"]]
    assert selected == [{"name": "gpt-4.1-mini", "provider": "openai", "source": "preset", "selected": True}]
    assert {"name": "local-model", "provider": "ollama", "source": "local", "selected": False, "size": 456} in payload["models"]
    assert {"name": "llama3.3", "provider": "ollama_cloud", "source": "cloud", "selected": False, "size": 123} in payload["models"]


def test_models_catalog_keeps_cloud_presets_without_api_key(monkeypatch):
    models_routes = _load_models_routes()

    from utils.settings import settings as runtime_settings

    monkeypatch.setattr(
        runtime_settings,
        "settings",
        {"OUTPUT_MODEL": "llama3.3", "OUTPUT_PROVIDER": "ollama_cloud"},
    )

    calls = []

    async def fake_fetch_tags(endpoint, headers=None):
        calls.append({"endpoint": endpoint, "headers": headers or {}})
        return [{"name": "local-only"}] if not headers else []

    async def fake_resolve_key(provider):
        # W1/SP4.1: siehe Begruendung in
        # test_models_catalog_returns_provider_aware_selected_model.
        assert provider in {"ollama_cloud", "openrouter", "minimax"}
        return ""

    monkeypatch.setattr(models_routes, "_fetch_tags", fake_fetch_tags)
    monkeypatch.setattr("core.llm_provider_client._resolve_cloud_api_key", fake_resolve_key)

    response = asyncio.run(models_routes.models_catalog())
    payload = _json_response_payload(response)

    assert any(row["name"] == "llama3.3" and row["provider"] == "ollama_cloud" for row in payload["models"])
    assert [row for row in payload["models"] if row["selected"]] == [
        {"name": "llama3.3", "provider": "ollama_cloud", "source": "preset", "selected": True}
    ]
    assert any(call["headers"] == {} for call in calls)


def test_output_provider_and_model_reach_complete_chat():
    seen = {}
    request = CoreChatRequest(
        model="gpt-4.1-mini",
        messages=[Message(role=MessageRole.USER, content="Hallo")],
        conversation_id="p1-provider",
        raw_request={"provider": "openai"},
    )
    plan = ThinkingPlan(
        plan_id="p1",
        intent="answer_user",
        steps=[PlanStep(step_id="s1", title="Antworten", goal="User beantworten")],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
    )
    output_request = OutputRequest(user_text="Hallo", thinking_plan=plan)

    async def fake_complete_chat(**kwargs):
        seen.update(kwargs)
        return {"content": "ok"}

    result = asyncio.run(complete_output(output_request, request, complete_chat_fn=fake_complete_chat))

    assert result.content == "ok"
    assert seen["provider"] == "openai"
    assert seen["model"] == "gpt-4.1-mini"
    assert {"role": "user", "content": "Hallo"} in seen["messages"]


def test_ollama_cloud_complete_chat_missing_key_is_explicit(monkeypatch, tmp_path):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_CLOUD_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_KEY", raising=False)
    monkeypatch.delenv("OLLAMA", raising=False)
    monkeypatch.delenv("INTERNAL_SECRET_RESOLVE_TOKEN", raising=False)
    monkeypatch.setattr("core.llm.secrets._env_or_dotenv", lambda name, default="": default)
    # W1/SP4.1: _DB_PATH zeigt produktionsseitig auf /app/data, das es in der
    # Test-Sandbox nicht gibt. Isolierung ueber tmp_path statt Produktionscode.
    monkeypatch.setattr(
        "utils.provider_keys_store._DB_PATH", tmp_path / "provider_keys.db"
    )

    from core import llm_provider_client

    llm_provider_client._API_KEY_CACHE.clear()

    with pytest.raises(RuntimeError, match="missing_api_key:ollama_cloud"):
        asyncio.run(
            llm_provider_client.complete_chat(
                provider="ollama_cloud",
                model="test-model",
                messages=[{"role": "user", "content": "Hallo"}],
            )
        )
