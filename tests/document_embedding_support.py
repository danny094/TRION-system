import importlib
import sys
from pathlib import Path

import pytest
import requests

from core.input_processor.chunker import chunk_document
from tests.conftest import env_or_dotenv
from tests.verifier_document_fixture_support import fixture_text

EMBED_MODEL = "hellord/mxbai-embed-large-v1:f16"


class _MiniMCP:
    def __init__(self):
        self.tools = {}

    def tool(self, fn):
        self.tools[fn.__name__] = fn
        return fn


def _live_embedding_target() -> dict[str, str]:
    cloud_enabled = env_or_dotenv("TRION_ENABLE_OLLAMA_CLOUD_TESTS", "").lower() in {"1", "true", "yes", "on"}
    cloud_key = env_or_dotenv("OLLAMA_API_KEY", "") or env_or_dotenv("OLLAMA_CLOUD_API_KEY", "")
    if cloud_enabled and cloud_key:
        return {
            "mode": "ollama_cloud",
            "base": env_or_dotenv("OLLAMA_CLOUD_BASE", "https://ollama.com").rstrip("/"),
            "api_key": cloud_key,
            "model": env_or_dotenv("TRION_OLLAMA_CLOUD_EMBED_MODEL", EMBED_MODEL).strip() or EMBED_MODEL,
        }
    return {
        "mode": "ollama",
        "base": env_or_dotenv("OLLAMA_BASE", "http://localhost:11434").rstrip("/"),
        "api_key": "",
        "model": env_or_dotenv("EMBEDDING_MODEL", EMBED_MODEL).strip() or EMBED_MODEL,
    }


def require_embedding_runtime() -> dict[str, str]:
    live = _live_embedding_target()
    headers = {"Authorization": f"Bearer {live['api_key']}"} if live["mode"] == "ollama_cloud" and live["api_key"] else None
    try:
        response = requests.get(f"{live['base']}/api/tags", headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as exc:
        pytest.skip(f"Ollama embedding endpoint unavailable: {exc}")
    names = {item.get("name") for item in response.json().get("models", [])}
    if live["model"] not in names:
        pytest.skip(f"Embedding model not available on {live['mode']}: {live['model']}")
    return live


def load_embedding_tools(monkeypatch, tmp_path: Path):
    live = require_embedding_runtime()
    memory_path = str(Path.cwd() / "memory")
    if memory_path not in sys.path:
        sys.path.insert(0, memory_path)

    monkeypatch.setenv("DB_PATH", str(tmp_path / "memory.db"))
    monkeypatch.setenv("OLLAMA_URL", live["base"])
    monkeypatch.setenv("EMBEDDING_MODEL", live["model"])
    monkeypatch.setenv("ADMIN_API_URL", "http://localhost:8200")
    if live["api_key"]:
        monkeypatch.setenv("OLLAMA_API_KEY", live["api_key"])

    import memory_mcp.config as memory_config
    import embedding
    import vector_store
    import memory_mcp.tool_groups.embedding_tools as embedding_tools

    importlib.reload(memory_config)
    importlib.reload(embedding)
    importlib.reload(vector_store)
    importlib.reload(embedding_tools)

    mini = _MiniMCP()
    embedding_tools.register_embedding_tools(mini)
    return mini.tools["memory_semantic_save"], mini.tools["memory_semantic_search"]


def index_document_for_embedding_search(name: str, semantic_save_tool, conversation_id: str) -> list[int]:
    entry_ids: list[int] = []
    for index, chunk in enumerate(chunk_document(fixture_text(name), max_tokens=120, overlap_tokens=20)):
        entry_id = 800 + index + 1
        entry_ids.append(entry_id)
        result = semantic_save_tool(
            conversation_id=conversation_id,
            content=chunk.content,
            content_type="document_chunk",
            key=f"document_chunk_{index}",
            value=f"chunk_index:{index};workspace_entry_id:{entry_id}",
        )
        assert result["success"] is True
    return entry_ids
