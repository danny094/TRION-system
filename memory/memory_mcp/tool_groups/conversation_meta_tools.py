from typing import Dict

from ..db.conversation_meta import (
    get_conversation_meta,
    upsert_conversation_meta,
    evaluate_long_term_write,
)


def register_conversation_meta_tools(mcp) -> None:

    @mcp.tool
    def conversation_meta_get(conversation_id: str) -> Dict:
        """Gibt persistierte Conversation-Metadaten zurück, wenn vorhanden."""
        meta = get_conversation_meta(conversation_id)
        return {"structuredContent": {"meta": meta}}

    @mcp.tool
    def conversation_meta_upsert(conversation_id: str, meta: Dict) -> Dict:
        """Erstellt oder aktualisiert Conversation-Metadaten."""
        saved = upsert_conversation_meta(conversation_id, meta)
        return {"structuredContent": {"meta": saved}}

    @mcp.tool
    def conversation_write_policy_check(conversation_id: str, layer: str = "ltm") -> Dict:
        """Prüft ob langfristiges Speichern für diese Conversation erlaubt ist."""
        return {"structuredContent": evaluate_long_term_write(conversation_id, layer)}
