from typing import Dict, List

from core.embedding_client import cosine_similarity, embed_text_sync
from core.orchestrator.contracts import ToolDescriptor

_EMBEDDING_CACHE: Dict[str, List[float] | None] = {}


def semantic_score(user_text: str, tool: ToolDescriptor) -> float | None:
    query_vec = _cached_embedding(str(user_text or ""))
    tool_vec = _cached_embedding(_tool_document(tool))
    if not query_vec or not tool_vec:
        return None
    return max(0.0, cosine_similarity(query_vec, tool_vec))


def _cached_embedding(text: str) -> List[float] | None:
    key = str(text or "").strip()
    if not key:
        return None
    if key not in _EMBEDDING_CACHE:
        vector = embed_text_sync(key)
        _EMBEDDING_CACHE[key] = list(vector) if isinstance(vector, list) and vector else None
    return _EMBEDDING_CACHE[key]


def _tool_document(tool: ToolDescriptor) -> str:
    parts = [tool.name, tool.intent_description or tool.description]
    parts.extend(tool.intent_examples)
    parts.extend(tool.intent_keywords)
    return " | ".join(part for part in parts if str(part or "").strip())
