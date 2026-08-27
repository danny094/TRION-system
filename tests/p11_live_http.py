from __future__ import annotations

import json
from urllib.parse import urljoin

import requests

from tests.conftest import env_or_dotenv

def backend_url() -> str:
    raw = env_or_dotenv("TRION_BACKEND_URL", "http://127.0.0.1:8200")
    return str(raw or "").rstrip("/") + "/"


def get_json(path: str, *, timeout: int = 20) -> dict:
    response = requests.get(urljoin(backend_url(), path.lstrip("/")), timeout=timeout)
    response.raise_for_status()
    data = response.json()
    assert isinstance(data, dict)
    return data


def post_chat_events(
    *,
    provider: str,
    model: str,
    conversation_id: str,
    messages: list[dict],
    timeout: int = 90,
) -> list[dict]:
    payload = {
        "model": model,
        "provider": provider,
        "conversation_id": conversation_id,
        "messages": messages,
        "stream": True,
    }
    response = requests.post(
        urljoin(backend_url(), "/api/chat"),
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=timeout,
    )
    assert response.status_code == 200, response.text
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert events, "No NDJSON events returned."
    return events
