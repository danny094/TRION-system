from config import CHUNK_MAX_TOKENS, CHUNK_OVERLAP_TOKENS
from core.input_processor.contracts import DocumentChunk


def chunk_document(
    user_text: str,
    *,
    max_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> list[DocumentChunk]:
    text = str(user_text or "").strip()
    if not text:
        return []
    raw_cap = int(max_tokens if max_tokens is not None else CHUNK_MAX_TOKENS)
    token_cap = max(1, raw_cap) if max_tokens is not None else max(50, raw_cap)
    overlap = max(0, int(overlap_tokens if overlap_tokens is not None else CHUNK_OVERLAP_TOKENS))
    words = text.split()
    if not words:
        return []
    step = max(1, token_cap - min(overlap, token_cap - 1))
    chunks: list[DocumentChunk] = []
    start = 0
    index = 0
    while start < len(words):
        end = min(len(words), start + token_cap)
        content = " ".join(words[start:end]).strip()
        if content:
            chunks.append(DocumentChunk(index=index, content=content, estimated_tokens=end - start))
            index += 1
        if end >= len(words):
            break
        start += step
    return chunks
