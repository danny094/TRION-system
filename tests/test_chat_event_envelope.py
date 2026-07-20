import importlib.util
import json
from pathlib import Path


def _chat_stream():
    path = Path(__file__).resolve().parents[1] / "adapters" / "admin-api" / "chat_stream.py"
    spec = importlib.util.spec_from_file_location("chat_stream_envelope_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_envelope_owns_conversation_id_and_ignores_payload_override():
    payload = json.loads(_chat_stream().event_to_ndjson(
        "model", "EXPECTED_CONVERSATION",
        {"type": "task_loop_state", "conversation_id": "PAYLOAD_SENTINEL", "state": "waiting"},
    ))

    assert payload["conversation_id"] == "EXPECTED_CONVERSATION"
    assert "PAYLOAD_SENTINEL" not in json.dumps(payload)
    assert payload["state"] == "waiting"
