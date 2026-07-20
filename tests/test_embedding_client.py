import httpx

from core.embedding_client import embed_text_sync
from core.embedding_transport import request_embedding_sync


class _Response:
    def __init__(self, status_code: int, data: dict):
        self.status_code = status_code
        self._data = data
        self.request = httpx.Request("POST", "http://test")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=self.request, response=self)

    def json(self) -> dict:
        return self._data


def test_request_embedding_sync_prefers_modern_embed_endpoint(monkeypatch):
    calls: list[tuple[str, dict]] = []

    class _Client:
        def __init__(self, timeout: float):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url: str, json: dict, headers=None):
            calls.append((url, json))
            return _Response(200, {"embeddings": [[0.1, 0.2, 0.3]]})

    monkeypatch.setattr("core.embedding_transport.httpx.Client", _Client)

    vector = request_embedding_sync(endpoint="https://ollama.com", model="m", text="hello", timeout_s=1.0)

    assert vector == [0.1, 0.2, 0.3]
    assert calls == [("https://ollama.com/api/embed", {"model": "m", "input": "hello"})]


def test_request_embedding_sync_falls_back_to_legacy_endpoint_on_404(monkeypatch):
    calls: list[tuple[str, dict]] = []

    class _Client:
        def __init__(self, timeout: float):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url: str, json: dict, headers=None):
            calls.append((url, json))
            if url.endswith("/api/embed"):
                return _Response(404, {})
            return _Response(200, {"embedding": [0.4, 0.5]})

    monkeypatch.setattr("core.embedding_transport.httpx.Client", _Client)

    vector = request_embedding_sync(endpoint="http://localhost:11434", model="m", text="hello", timeout_s=1.0)

    assert vector == [0.4, 0.5]
    assert calls == [
        ("http://localhost:11434/api/embed", {"model": "m", "input": "hello"}),
        ("http://localhost:11434/api/embeddings", {"model": "m", "prompt": "hello"}),
    ]


def test_embed_text_sync_uses_cloud_fallback_when_local_embedding_missing(monkeypatch):
    calls: list[tuple[str, str, dict | None]] = []

    monkeypatch.setattr(
        "core.embedding_client.resolve_role_endpoint",
        lambda role, default_endpoint="": {"hard_error": False, "endpoint": "http://local-ollama"},
    )
    monkeypatch.setattr("core.embedding_client.get_embedding_model", lambda: "local-model")
    monkeypatch.setattr("core.embedding_client.get_embedding_cloud_fallback_enable", lambda: True)
    monkeypatch.setattr("core.embedding_client.get_embedding_cloud_fallback_model", lambda: "cloud-model")
    monkeypatch.setattr("core.embedding_client.ollama_cloud_base", lambda: "https://ollama.com")
    monkeypatch.setattr("core.embedding_client._cloud_headers", lambda: {"Authorization": "Bearer test"})

    def _fake_request(endpoint: str, model: str, text: str, timeout_s: float, headers=None, label="local"):
        calls.append((endpoint, model, headers))
        if endpoint == "http://local-ollama":
            return None
        return [0.9, 0.8]

    monkeypatch.setattr("core.embedding_client.request_embedding_sync", _fake_request)

    vector = embed_text_sync("hello", timeout_s=0.5)

    assert vector == [0.9, 0.8]
    assert calls == [
        ("http://local-ollama", "local-model", None),
        ("https://ollama.com", "cloud-model", {"Authorization": "Bearer test"}),
    ]
