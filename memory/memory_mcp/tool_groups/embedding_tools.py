import os
from typing import Dict, List, Optional

from ..db.conversation_meta import evaluate_retrieval_policy

_RETRIEVAL_FILTER = os.getenv("MEMORY_RETRIEVAL_FILTER_ENABLE", "false").strip().lower() in ("1", "true", "yes")


def _resolve_scoped_id(conversation_id: Optional[str]) -> tuple[bool, Optional[str]]:
    """Gibt (allowed, effective_conversation_id) zurück."""
    if not _RETRIEVAL_FILTER or not conversation_id:
        return True, conversation_id
    result = evaluate_retrieval_policy(conversation_id)
    if not result["allowed"]:
        return False, None
    if result.get("conversation_scoped"):
        return True, conversation_id
    return True, conversation_id


def register_embedding_tools(mcp) -> None:

    @mcp.tool
    def memory_semantic_save(
        conversation_id: str,
        content: str,
        content_type: str = "fact",
        key: str = None,
        value: str = None,
    ) -> Dict:
        """Speichert einen Eintrag mit Embedding für semantische Suche."""
        from vector_store import get_vector_store
        vs = get_vector_store()
        metadata = {}
        if key:
            metadata["key"] = key
        if value:
            metadata["value"] = value
        entry_id = vs.add(
            conversation_id=conversation_id, content=content,
            content_type=content_type, metadata=metadata,
        )
        return {"success": bool(entry_id), "id": entry_id} if entry_id else {"success": False, "error": "Could not save"}

    @mcp.tool
    def tool_embedding_save(
        tool_name: str,
        description: str,
        capabilities: List[str],
    ) -> Dict:
        """Speichert eine Tool-Definition für semantische Suche."""
        from vector_store import get_vector_store
        cap_str = ", ".join(capabilities)
        content = f"Tool: {tool_name}\nDescription: {description}\nCapabilities: {cap_str}"
        try:
            get_vector_store().add(
                conversation_id="global", content=content,
                content_type="tool_def",
                metadata={"tool_name": tool_name, "capabilities": capabilities, "description": description},
            )
            return {"result": f"Tool {tool_name} vectorized"}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def memory_semantic_search(
        query: str,
        conversation_id: str = None,
        limit: int = 5,
        min_similarity: float = 0.5,
        content_type: Optional[str] = None,
        allow_mixed_versions: bool = False,
        embedding_version: Optional[str] = None,
    ) -> Dict:
        """Semantische Suche — findet ähnliche Einträge nach Bedeutung."""
        allowed, effective_id = _resolve_scoped_id(conversation_id)
        if not allowed:
            return {"results": [], "count": 0, "denied": True, "reason": "retrieval_blocked_by_policy"}
        from vector_store import get_vector_store
        results = get_vector_store().search(
            query=query, conversation_id=effective_id, limit=limit,
            min_similarity=min_similarity, content_type=content_type,
            allow_mixed_versions=allow_mixed_versions, embedding_version=embedding_version,
        )
        return {"results": results, "count": len(results)}

    @mcp.tool
    def memory_embedding_version_status(
        conversation_id: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Dict:
        """Zeigt aktive/stale Embedding-Versionen für Monitoring."""
        from vector_store import get_vector_store
        return get_vector_store().get_version_status(
            conversation_id=conversation_id, content_type=content_type,
        )

    @mcp.tool
    def memory_embedding_backfill(
        batch_size: int = 100,
        conversation_id: Optional[str] = None,
        content_type: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict:
        """Re-embedding Batch für veraltete/fehlende Embeddings. Resume-fähig."""
        from vector_store import get_vector_store
        return get_vector_store().backfill_embeddings(
            batch_size=max(1, min(int(batch_size), 1000)),
            conversation_id=conversation_id,
            content_type=content_type,
            dry_run=bool(dry_run),
        )
