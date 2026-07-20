import re

from core.input_processor.contracts import DocumentChunk


def detect_document_candidates(chunks: list[DocumentChunk]) -> dict[str, list[int]]:
    index_like: list[int] = []
    chapter_candidates: list[int] = []
    for chunk in chunks:
        text = str(chunk.content or "")
        lowered = text.lower()
        if _looks_like_index(text, lowered):
            index_like.append(chunk.index)
        if _looks_like_chapter_chunk(text, lowered):
            chapter_candidates.append(chunk.index)
    return {
        "index_like_indexes": index_like,
        "chapter_candidate_indexes": _dedupe(index_like + chapter_candidates),
    }


def _looks_like_index(text: str, lowered: str) -> bool:
    if any(token in lowered for token in ("inhaltsverzeichnis", "contents", "table of contents")):
        return True
    toc_lines = re.findall(r"(?m)^.{3,80}\.{3,}\s*\d+\s*$", text)
    return len(toc_lines) >= 3


def _looks_like_chapter_chunk(text: str, lowered: str) -> bool:
    if any(token in lowered for token in ("kapitel", "chapter", "abschnitt", "teil")):
        return True
    heading_lines = re.findall(r"(?m)^(?:\d+[\.\)]\s+|kapitel\s+\d+|chapter\s+\d+).+$", lowered)
    return len(heading_lines) >= 2


def _dedupe(values: list[int]) -> list[int]:
    ordered: list[int] = []
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return ordered
