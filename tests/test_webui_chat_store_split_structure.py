from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHAT_STATE_DIR = ROOT / "adapters" / "webui" / "src" / "features" / "chat" / "state"
CHAT_STORE_PATH = CHAT_STATE_DIR / "chatStore.ts"
CHAT_STREAMING_PATH = CHAT_STATE_DIR / "chatMessageStreaming.ts"
CHAT_TYPES_PATH = CHAT_STATE_DIR.parent / "types.ts"


def test_chat_store_split_preserves_single_state_owner() -> None:
    store_source = CHAT_STORE_PATH.read_text(encoding="utf-8")
    streaming_source = CHAT_STREAMING_PATH.read_text(encoding="utf-8")

    assert store_source.count("create<ChatState>") == 1
    assert "export const useChatStore" in store_source
    assert "create<ChatState>" not in streaming_source
    assert "sendMessage: createSendMessageAction(set, get)" in store_source
    assert "approveWaitingTask: async" in store_source


def test_chat_store_split_respects_doc07() -> None:
    for path in (CHAT_STORE_PATH, CHAT_STREAMING_PATH, CHAT_TYPES_PATH):
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 200
