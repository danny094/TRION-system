from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    index: int
    content: str
    estimated_tokens: int


@dataclass(frozen=True)
class DocumentContext:
    conversation_id: str
    summary: str
    key_facts: list[str]
    total_chunks: int
    workspace_entry_ids: list[int]
    preferred_entry_ids: list[int]
    index_like_entry_ids: list[int]
    chapter_candidate_entry_ids: list[int]
    original_char_count: int
    semantic_keys: list[str]
    semantic_candidate_keys: list[str]
