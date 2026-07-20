from pathlib import Path

from core.input_processor import process_long_input
from core.models import CoreChatRequest, Message, MessageRole

FIXTURE_PATH = Path(__file__).with_name("documententest.md")


def fixture_text() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def request_from_fixture() -> CoreChatRequest:
    return CoreChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content=fixture_text())],
        conversation_id="documententest",
        source_adapter="pytest",
    )


def document_context_from_fixture():
    seen = {"workspace": 0}

    def save_workspace(*_args):
        seen["workspace"] += 1
        return 200 + seen["workspace"]

    return process_long_input(
        fixture_text(),
        conversation_id="documententest",
        workspace_save_fn=save_workspace,
        semantic_save_fn=lambda *_: {"success": True},
        max_tokens=500,
        overlap_tokens=50,
    )


def enable_documententest_chunking(monkeypatch) -> None:
    monkeypatch.setattr("core.classifier.classifier.ENABLE_CHUNKING", True)
    monkeypatch.setattr("core.classifier.classifier.CHUNKING_THRESHOLD", 4000)
    monkeypatch.setattr("core.input_processor.chunker.CHUNK_MAX_TOKENS", 500)
    monkeypatch.setattr("core.input_processor.chunker.CHUNK_OVERLAP_TOKENS", 50)
