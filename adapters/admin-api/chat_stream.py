import json
from datetime import datetime, timezone

from core.pipeline.public_projection import REJECTION_ERROR_CODE, REJECTION_MESSAGE


def response_to_ndjson(response, *, content_already_streamed: bool = False):
    done_reason = str(getattr(response, "done_reason", "stop") or "stop")
    model = str(getattr(response, "model", "") or "")
    conversation_id = str(getattr(response, "conversation_id", "global") or "global")
    content = str(getattr(response, "content", "") or "")

    if content and done_reason not in {"blocked", "rejected"}:
        if content_already_streamed:
            yield event_to_ndjson(
                model,
                conversation_id,
                {"type": "final_content", "content": content},
            )
        else:
            yield event_to_ndjson(
                model,
                conversation_id,
                {"type": "content", "content": content},
            )

    if done_reason in {"blocked", "rejected"}:
        payload = {
            "type": done_reason,
            "content": REJECTION_MESSAGE,
            "error_code": REJECTION_ERROR_CODE,
        }
        yield event_to_ndjson(model, conversation_id, payload)

    yield _done_line(model, conversation_id, done_reason)


def error_to_ndjson(exc, *, model: str, conversation_id: str) -> str:
    payload = _error_payload(exc)
    return "".join(
        [
            event_to_ndjson(
                model,
                conversation_id,
                {"type": "error", **payload},
            ),
            _done_line(model, conversation_id, "error"),
        ]
    )


def event_to_ndjson(model: str, conversation_id: str, payload: dict, *, done: bool = False) -> str:
    public_payload = dict(payload or {})
    public_payload.pop("conversation_id", None)
    return json.dumps(
        {
            **public_payload,
            "model": model,
            "conversation_id": conversation_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "done": done,
        },
        ensure_ascii=False,
    ) + "\n"


def _done_line(model: str, conversation_id: str, done_reason: str) -> str:
    return event_to_ndjson(
        model,
        conversation_id,
        {"type": "done", "done_reason": done_reason or "stop"},
        done=True,
    )


def _error_payload(exc) -> dict:
    del exc
    return {
        "content": "Ein interner Fehler ist aufgetreten.",
        "error_code": "internal_error",
    }
