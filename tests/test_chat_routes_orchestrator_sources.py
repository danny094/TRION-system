"""Verify the admin-api chat route forwards default orchestrator context sources."""

import asyncio
import importlib.util
import sys
from pathlib import Path

from core.models import CoreChatResponse


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _load_chat_routes():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    spec = importlib.util.spec_from_file_location(
        "trion_chat_routes_for_sources_test",
        ADMIN_API_DIR / "chat_routes.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Request:
    async def json(self):
        return {
            "model": "test-model",
            "conversation_id": "conv-src",
            "messages": [{"role": "user", "content": "Status?"}],
            "stream": True,
        }


async def _drain(response):
    async for _ in response.body_iterator:
        pass


def test_chat_route_forwards_default_orchestrator_context_sources(monkeypatch):
    chat_routes = _load_chat_routes()
    captured_kwargs = {}

    async def fake_run_chat(core_request, **kwargs):
        captured_kwargs.update(kwargs)
        return CoreChatResponse(
            model="test-model",
            content="ok",
            conversation_id="conv-src",
            done=True,
            done_reason="stop",
        )

    monkeypatch.setattr("core.pipeline.runner.run_chat", fake_run_chat)
    response = asyncio.run(chat_routes.chat(_Request()))
    asyncio.run(_drain(response))

    sources = captured_kwargs.get("orchestrator_context_sources")
    assert isinstance(sources, dict)
    assert set(sources.keys()) == {"memory", "conversation_meta", "runtime", "active_containers"}
    for name, source in sources.items():
        assert callable(source), f"{name} must be callable"
