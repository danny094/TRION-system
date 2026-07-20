"""Dockerfile-Parser-Regressionstest: tool_intents.json muss in Admin-API-Container kopiert werden.

Wurzel: adapters/tool_runner_bridge._tool_intent_for() liest tool_intents.json aus dem
MCP-Bundle-Verzeichnis. Fehlt die Datei im Container, defaultet tool_role auf 'primary'
für alle Tools — inklusive Tools mit tool_role=forbidden_direct (z. B. graph_find_duplicate_nodes).

Kein docker build notwendig; der Fehler ist statisch im Dockerfile belegbar.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "adapters" / "admin-api" / "Dockerfile"


def test_dockerfile_copies_tool_intents_json():
    source = DOCKERFILE.read_text(encoding="utf-8")
    assert "COPY memory/memory_mcp/tool_intents.json /app/memory/memory_mcp/tool_intents.json" in source
