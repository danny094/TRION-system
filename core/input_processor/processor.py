from core.input_processor.chunker import chunk_document
from core.input_processor.contracts import DocumentContext
from core.input_processor.storage import (
    SemanticSaveFn,
    WorkspaceSaveFn,
    store_semantic_chunks,
    store_workspace_chunks,
)
from core.input_processor.summarizer import build_document_context


def process_long_input(
    user_text: str,
    *,
    conversation_id: str = "",
    workspace_save_fn: WorkspaceSaveFn | None = None,
    semantic_save_fn: SemanticSaveFn | None = None,
    max_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> DocumentContext:
    chunks = chunk_document(user_text, max_tokens=max_tokens, overlap_tokens=overlap_tokens)
    workspace_entry_ids = store_workspace_chunks(chunks, conversation_id, workspace_save_fn)
    semantic_keys = store_semantic_chunks(
        chunks,
        conversation_id,
        semantic_save_fn,
        workspace_entry_ids=workspace_entry_ids,
    )
    return build_document_context(
        user_text,
        conversation_id=conversation_id,
        chunks=chunks,
        workspace_entry_ids=workspace_entry_ids,
        semantic_keys=semantic_keys,
    )
