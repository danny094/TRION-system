import sqlite3
from typing import Dict, List

from ..config import DB_PATH


def register_memory_admin_tools(mcp) -> None:

    @mcp.tool
    def memory_delete(id: int) -> str:
        """Löscht einen Memory-Eintrag per ID."""
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.execute("DELETE FROM memory WHERE id = ?", (id,))
            conn.commit()
            return f"Deleted {id}" if cur.rowcount > 0 else f"Not found {id}"
        finally:
            conn.close()

    @mcp.tool
    def memory_all_recent(limit: int = 500) -> Dict:
        """Alle neuesten Memory-Einträge konversationsübergreifend."""
        conn = sqlite3.connect(DB_PATH)
        try:
            rows = conn.execute(
                "SELECT id, conversation_id, content, created_at FROM memory ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            entries = [{"id": r[0], "conversation_id": r[1], "content": r[2], "created_at": r[3]} for r in rows]
            return {"structuredContent": {"entries": entries, "count": len(entries), "limit": limit}}
        except Exception as e:
            return {"error": str(e), "entries": []}
        finally:
            conn.close()

    @mcp.tool
    def memory_list_conversations(limit: int = 100) -> Dict:
        """Listet alle Conversations mit Eintragszahl."""
        conn = sqlite3.connect(DB_PATH)
        try:
            rows = conn.execute(
                """
                SELECT conversation_id, COUNT(*) as entry_count, MAX(created_at) as last_updated
                FROM memory GROUP BY conversation_id ORDER BY last_updated DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            conversations = [{"conversation_id": r[0], "entry_count": r[1], "last_updated": r[2]} for r in rows]
            return {"structuredContent": {"conversations": conversations, "total": len(conversations)}}
        finally:
            conn.close()

    @mcp.tool
    def memory_delete_bulk(ids: List[int]) -> Dict:
        """Löscht mehrere Memory-Einträge auf einmal."""
        conn = sqlite3.connect(DB_PATH)
        try:
            deleted_count = 0
            for entry_id in ids:
                cur = conn.execute("DELETE FROM memory WHERE id = ?", (entry_id,))
                if cur.rowcount > 0:
                    deleted_count += 1
            conn.commit()
            return {"structuredContent": {"deleted": deleted_count, "total_requested": len(ids)}}
        except Exception as e:
            return {"error": str(e), "deleted": 0}
        finally:
            conn.close()

    @mcp.tool
    def memory_reset() -> Dict:
        """Löscht ALLE Memory-Einträge, Graph-Nodes und Edges. IRREVERSIBEL."""
        conn = sqlite3.connect(DB_PATH)
        try:
            memory_count = conn.execute("DELETE FROM memory").rowcount
            edges_count = conn.execute("DELETE FROM graph_edges").rowcount
            nodes_count = conn.execute("DELETE FROM graph_nodes").rowcount
            try:
                conn.execute("DELETE FROM memory_fts")
            except Exception:
                pass
            conn.commit()
        finally:
            conn.close()
        try:
            from vector_store import get_vector_store
            vs = get_vector_store()
            if hasattr(vs, "reset"):
                vs.reset()
            elif hasattr(vs, "clear"):
                vs.clear()
        except Exception as e:
            print(f"[memory_reset] Vector store reset failed: {e}")
        return {"structuredContent": {"success": True, "memory_entries": memory_count, "graph_nodes": nodes_count, "graph_edges": edges_count}}
