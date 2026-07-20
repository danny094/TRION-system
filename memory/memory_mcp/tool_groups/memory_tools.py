import os
import sqlite3
from typing import Dict, List, Optional, Tuple

from ..config import DB_PATH
from ..db.conversation_meta import evaluate_long_term_write, evaluate_retrieval_policy
from ..db.memory import insert_row, row_to_memory_dict
from ..db.facts import insert_fact, load_fact
from ..auto_layer import auto_assign_layer

_RETRIEVAL_FILTER = os.getenv("MEMORY_RETRIEVAL_FILTER_ENABLE", "false").strip().lower() in ("1", "true", "yes")


def _retrieval_gate(conversation_id: Optional[str]) -> Tuple[bool, Optional[str]]:
    """(allowed, forced_id). forced_id gesetzt wenn scope auf conversation eingeschränkt."""
    if not _RETRIEVAL_FILTER or not conversation_id:
        return True, None
    result = evaluate_retrieval_policy(conversation_id)
    if not result["allowed"]:
        return False, None
    return True, conversation_id if result.get("conversation_scoped") else None


def register_memory_tools(mcp) -> None:

    @mcp.tool
    def memory_save(conversation_id: str, role: str, content: str,
                    tags: Optional[str] = None, layer: Optional[str] = None) -> Dict:
        """Speichert freien Text."""
        role_norm = role.lower()
        if not layer or layer == "auto":
            layer = auto_assign_layer(role_norm, content)
        write_check = evaluate_long_term_write(conversation_id, layer)
        if not write_check["allowed"]:
            return {"result": "Memory write denied by conversation policy",
                    "structuredContent": {"saved": False, "denied": True,
                                          "reason": write_check["reason"], "layer": layer,
                                          "policy": write_check["policy"]}}
        new_id = insert_row(conversation_id, role_norm, content, tags, layer)
        try:
            from vector_store import get_vector_store
            get_vector_store().add(conversation_id=conversation_id, content=content,
                                   content_type="memory", metadata={"role": role_norm, "layer": layer})
        except Exception as e:
            print(f"[memory_save] Embedding failed: {e}")
        return {"result": f"Saved memory {new_id}",
                "structuredContent": {"id": new_id, "layer": layer, "content": content}}

    @mcp.tool
    def memory_fact_save(conversation_id: str, key: str, value: str,
                         subject: str = "Danny", layer: str = "ltm") -> Dict:
        """Speichert strukturierte Fakten."""
        write_check = evaluate_long_term_write(conversation_id, layer)
        if not write_check["allowed"]:
            return {"result": "Fact write denied by conversation policy",
                    "structuredContent": {"saved": False, "denied": True, "reason": write_check["reason"],
                                          "layer": layer, "policy": write_check["policy"],
                                          "subject": subject, "key": key, "value": value}}
        new_id = insert_fact(conversation_id, subject, key, value, layer)
        content = f"{subject} {key}: {value}"
        embedding = None
        try:
            from embedding import get_embedding
            from vector_store import get_vector_store
            embedding = get_embedding(content)
            get_vector_store().add(conversation_id=conversation_id, content=content, content_type="fact",
                                   metadata={"key": key, "value": value, "subject": subject})
        except Exception as e:
            print(f"[memory_fact_save] Embedding failed: {e}")
        try:
            from graph import build_node_with_edges
            build_node_with_edges(source_type="fact", content=content, source_id=new_id,
                                  embedding=embedding, conversation_id=conversation_id, related_keys=[key])
        except Exception as e:
            print(f"[memory_fact_save] Graph failed: {e}")
        return {"result": f"Fact saved {new_id}",
                "structuredContent": {"id": new_id, "subject": subject, "key": key, "value": value, "layer": layer}}

    @mcp.tool
    def memory_fact_load(conversation_id: str, key: str) -> Dict:
        """Lädt einen strukturierten Fakt."""
        allowed, _ = _retrieval_gate(conversation_id)
        if not allowed:
            return {"result": None, "structuredContent": {"denied": True, "reason": "retrieval_blocked_by_policy"}}
        return {"result": load_fact(conversation_id, key), "structuredContent": {"key": key}}

    @mcp.tool
    def memory_recent(conversation_id: str, limit: int = 20) -> List[Dict]:
        """Gibt die neuesten Memory-Einträge zurück."""
        allowed, _ = _retrieval_gate(conversation_id)
        if not allowed:
            return []
        conn = sqlite3.connect(DB_PATH)
        try:
            rows = conn.execute("SELECT * FROM memory WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                                (conversation_id, limit)).fetchall()
            return [row_to_memory_dict(r) for r in rows]
        finally:
            conn.close()

    @mcp.tool
    def memory_search(query: str, conversation_id: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Einfache Text-Suche im Memory (LIKE)."""
        allowed, forced_id = _retrieval_gate(conversation_id)
        if not allowed:
            return []
        effective_id = forced_id or conversation_id
        like = f"%{query}%"
        conn = sqlite3.connect(DB_PATH)
        try:
            if effective_id:
                rows = conn.execute("SELECT * FROM memory WHERE conversation_id = ? AND content LIKE ? ORDER BY id DESC LIMIT ?",
                                    (effective_id, like, limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM memory WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                                    (like, limit)).fetchall()
            return [row_to_memory_dict(r) for r in rows]
        finally:
            conn.close()

    @mcp.tool
    def memory_search_layered(conversation_id: str, query: str, limit: int = 20) -> List[Dict]:
        """Schichtweise Memory-Suche (stm → mtm → ltm)."""
        allowed, _ = _retrieval_gate(conversation_id)
        if not allowed:
            return []
        like = f"%{query}%"
        results: List[Dict] = []
        conn = sqlite3.connect(DB_PATH)
        try:
            for layer in ("stm", "mtm", "ltm"):
                remaining = limit - len(results)
                if remaining <= 0:
                    break
                rows = conn.execute("SELECT * FROM memory WHERE conversation_id = ? AND layer = ? AND content LIKE ? ORDER BY id DESC LIMIT ?",
                                    (conversation_id, layer, like, remaining)).fetchall()
                results.extend(row_to_memory_dict(r) for r in rows)
            return results[:limit]
        finally:
            conn.close()

    @mcp.tool
    def memory_search_fts(query: str, conversation_id: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Volltext-Suche via FTS5."""
        allowed, forced_id = _retrieval_gate(conversation_id)
        if not allowed:
            return []
        effective_id = forced_id or conversation_id
        conn = sqlite3.connect(DB_PATH)
        try:
            if effective_id:
                rows = conn.execute("SELECT m.* FROM memory_fts f JOIN memory m ON m.id = f.rowid WHERE f MATCH ? AND f.conversation_id = ? ORDER BY rank LIMIT ?",
                                    (query, effective_id, limit)).fetchall()
            else:
                rows = conn.execute("SELECT m.* FROM memory_fts f JOIN memory m ON m.id = f.rowid WHERE f MATCH ? ORDER BY rank LIMIT ?",
                                    (query, limit)).fetchall()
            return [row_to_memory_dict(r) for r in rows]
        finally:
            conn.close()

    @mcp.tool
    def memory_autosave_hook(conversation_id: str, message: str) -> str:
        """Autosave-Hook für User-Nachrichten."""
        insert_row(conversation_id, "user", message, tags="", layer="auto")
        return "OK"
