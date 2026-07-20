from core.input_processor.contracts import DocumentChunk, DocumentContext
from core.input_processor.signals import detect_document_candidates


def build_document_context(
    user_text: str,
    *,
    conversation_id: str = "",
    chunks: list[DocumentChunk] | None = None,
    workspace_entry_ids: list[int] | None = None,
    semantic_keys: list[str] | None = None,
) -> DocumentContext:
    text = str(user_text or "").strip()
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    key_facts = _extract_key_facts(paragraphs)
    summary = _build_summary(paragraphs, key_facts, chunks or [])
    candidate_map = detect_document_candidates(chunks or [])
    index_like_entry_ids = _map_chunk_indexes(candidate_map.get("index_like_indexes", []), workspace_entry_ids or [])
    chapter_candidate_entry_ids = _map_chunk_indexes(candidate_map.get("chapter_candidate_indexes", []), workspace_entry_ids or [])
    semantic_candidate_keys = _map_chunk_indexes(candidate_map.get("chapter_candidate_indexes", []), semantic_keys or [])
    return DocumentContext(
        conversation_id=str(conversation_id or ""),
        summary=summary,
        key_facts=key_facts,
        total_chunks=len(chunks) if chunks is not None else (max(1, len(paragraphs)) if text else 0),
        workspace_entry_ids=list(workspace_entry_ids or []),
        preferred_entry_ids=_preferred_entry_ids(index_like_entry_ids, chapter_candidate_entry_ids, workspace_entry_ids or []),
        index_like_entry_ids=index_like_entry_ids,
        chapter_candidate_entry_ids=chapter_candidate_entry_ids,
        original_char_count=len(text),
        semantic_keys=list(semantic_keys or []),
        semantic_candidate_keys=semantic_candidate_keys or list(semantic_keys or [])[:3],
    )


def _extract_key_facts(paragraphs: list[str]) -> list[str]:
    facts = []
    for paragraph in paragraphs[:6]:
        line = " ".join(paragraph.split())
        if not line:
            continue
        facts.append(line[:160])
        if len(facts) >= 4:
            break
    return facts


def _build_summary(paragraphs: list[str], key_facts: list[str], chunks: list[DocumentChunk]) -> str:
    if not paragraphs:
        return ""
    first = " ".join(paragraphs[0].split())[:280]
    last = " ".join(paragraphs[-1].split())[:220] if len(paragraphs) > 1 else ""
    parts = [f"Dokumentzusammenfassung fuer Planning: {first}"]
    if chunks:
        parts.append(f"Chunk-Anzahl: {len(chunks)}")
    if last and last != first:
        parts.append(f"Letzter Abschnitt: {last}")
    if key_facts:
        parts.append("Kernpunkte: " + " | ".join(key_facts[:3]))
    return "\n".join(parts)[:900]


def _map_chunk_indexes(indexes: list[int], values: list[int] | list[str]) -> list[int] | list[str]:
    mapped = []
    for index in indexes:
        if 0 <= index < len(values):
            mapped.append(values[index])
    return mapped


def _preferred_entry_ids(
    index_like_entry_ids: list[int],
    chapter_candidate_entry_ids: list[int],
    workspace_entry_ids: list[int],
) -> list[int]:
    if index_like_entry_ids:
        return list(index_like_entry_ids[:4])
    if chapter_candidate_entry_ids:
        return list(chapter_candidate_entry_ids[:4])
    return list(workspace_entry_ids[:3])
