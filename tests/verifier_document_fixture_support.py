from pathlib import Path

from core.input_processor.chunker import chunk_document
from core.input_processor import process_long_input

FIXTURE_DIR = Path(__file__).with_name("Dokumententest")


def fixture_text(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def document_context(name: str):
    seen = {"workspace": 0}

    def save_workspace(*_args):
        seen["workspace"] += 1
        return 800 + seen["workspace"]

    return process_long_input(
        fixture_text(name),
        conversation_id=f"verifier-{name}",
        workspace_save_fn=save_workspace,
        semantic_save_fn=lambda *_args: {"success": True},
        max_tokens=120,
        overlap_tokens=20,
    )


def chunk_entry_ids(name: str) -> list[int]:
    chunks = chunk_document(fixture_text(name), max_tokens=120, overlap_tokens=20)
    return [800 + index + 1 for index in range(len(chunks))]


def entry_id_for_phrase(name: str, phrase: str) -> int:
    chunks = chunk_document(fixture_text(name), max_tokens=120, overlap_tokens=20)
    lowered_phrase = phrase.lower()
    for index, chunk in enumerate(chunks):
        if lowered_phrase in str(chunk.content or "").lower():
            return 800 + index + 1
    return 0
