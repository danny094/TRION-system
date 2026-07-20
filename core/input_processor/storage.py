from typing import Callable, Optional

from core.input_processor.contracts import DocumentChunk

WorkspaceSaveFn = Callable[[str, str, str, str], int]
SemanticSaveFn = Callable[[str, str, str, Optional[str], Optional[str]], object]


def store_workspace_chunks(
    chunks: list[DocumentChunk],
    conversation_id: str,
    workspace_save_fn: WorkspaceSaveFn | None,
) -> list[int]:
    if not callable(workspace_save_fn) or not conversation_id:
        return []
    entry_ids: list[int] = []
    for chunk in chunks:
        entry_ids.append(
            int(
                workspace_save_fn(
                    conversation_id,
                    chunk.content,
                    "document_chunk",
                    "input_processor",
                )
            )
        )
    return entry_ids


def store_semantic_chunks(
    chunks: list[DocumentChunk],
    conversation_id: str,
    semantic_save_fn: SemanticSaveFn | None,
    workspace_entry_ids: list[int] | None = None,
) -> list[str]:
    if not callable(semantic_save_fn) or not conversation_id:
        return []
    semantic_keys: list[str] = []
    for chunk in chunks:
        key = f"document_chunk_{chunk.index}"
        workspace_entry_id = _workspace_entry_id_for_chunk(chunk.index, workspace_entry_ids or [])
        semantic_save_fn(
            conversation_id,
            chunk.content,
            "document_chunk",
            key,
            _semantic_value(chunk.index, workspace_entry_id),
        )
        semantic_keys.append(key)
    return semantic_keys


def _workspace_entry_id_for_chunk(chunk_index: int, workspace_entry_ids: list[int]) -> int:
    if 0 <= chunk_index < len(workspace_entry_ids):
        return int(workspace_entry_ids[chunk_index] or 0)
    return 0


def _semantic_value(chunk_index: int, workspace_entry_id: int) -> str:
    parts = [f"chunk_index:{chunk_index}"]
    if workspace_entry_id > 0:
        parts.append(f"workspace_entry_id:{workspace_entry_id}")
    return ";".join(parts)
