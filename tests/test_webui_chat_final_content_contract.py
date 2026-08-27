from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHAT_EVENTS_PATH = ROOT / "adapters" / "webui" / "src" / "lib" / "contracts" / "chatEvents.ts"
CHAT_STREAMING_PATH = (
    ROOT
    / "adapters"
    / "webui"
    / "src"
    / "features"
    / "chat"
    / "state"
    / "chatMessageStreaming.ts"
)


def test_final_content_remains_a_typed_public_event() -> None:
    source = CHAT_EVENTS_PATH.read_text(encoding="utf-8")

    assert "export interface FinalContentEvent" in source
    assert "type: 'final_content'" in source
    assert "| FinalContentEvent" in source


def test_chat_store_replaces_final_content_instead_of_appending() -> None:
    source = CHAT_STREAMING_PATH.read_text(encoding="utf-8")

    assert "if (event.type === 'content')" in source
    assert "asstMsg.content += getEventContent(event)" in source
    assert "else if (event.type === 'final_content')" in source
    assert "asstMsg.content = getEventContent(event)" in source
    assert "asstMsg.content += getEventContent(event)\n            } else if (event.type === 'error')" not in source
