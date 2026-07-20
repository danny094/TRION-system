import json
from typing import Dict, List, Optional


def register_graph_tools(mcp) -> None:

    @mcp.tool
    def memory_graph_search(
        query: str,
        conversation_id: str = None,
        depth: int = 2,
        limit: int = 10,
    ) -> Dict:
        """Graph-basierte Suche — findet verbundene Informationen."""
        from vector_store import get_vector_store
        from graph import get_graph_store
        vs = get_vector_store()
        gs = get_graph_store()
        seed_results = vs.search(query=query, conversation_id=conversation_id, limit=5, min_similarity=0.5)
        if not seed_results:
            return {"results": [], "count": 0}
        seed_node_ids = []
        all_known_types = ["fact", "skill", "event", "note", "observation", "task"]
        for seed in seed_results:
            seed_text = seed["content"][:80]
            found = False
            for t in all_known_types:
                for node in gs.get_nodes_by_type(t, limit=50):
                    if seed_text in node["content"] or node["content"][:80] in seed_text:
                        seed_node_ids.append(node["id"])
                        found = True
                        break
                if found:
                    break
        if not seed_node_ids:
            return {"results": seed_results, "count": len(seed_results), "source": "semantic_only"}
        graph_results = gs.graph_walk(start_node_ids=seed_node_ids, depth=depth, limit=limit)
        live_results = [n for n in graph_results if "tombstone" not in (n.get("content") or "").lower()]
        seen: dict = {}
        for n in live_results:
            sid = n.get("source_id") or ""
            if not sid:
                continue
            if seen.get(sid) is None or n.get("confidence", 0.5) > seen[sid].get("confidence", 0.5):
                seen[sid] = n
        deduped = [n for n in live_results if not n.get("source_id") or seen.get(n.get("source_id")) is n]
        combined = [{"content": n["content"], "type": n["source_type"], "depth": n.get("depth", 0), "node_id": n["id"]} for n in deduped]
        return {"results": combined, "count": len(combined), "source": "graph_walk"}

    @mcp.tool
    def memory_graph_neighbors(
        node_id: int,
        edge_type: str = None,
        direction: str = "outgoing",
    ) -> Dict:
        """Gibt Nachbarn eines Graph-Nodes zurück."""
        from graph import get_graph_store
        neighbors = get_graph_store().get_neighbors(node_id=node_id, edge_type=edge_type, direction=direction)
        return {"neighbors": neighbors, "count": len(neighbors)}

    @mcp.tool
    def memory_graph_stats() -> Dict:
        """Gibt Graph-Statistiken zurück."""
        import sqlite3
        from ..config import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        try:
            node_count = conn.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]
            edge_count = conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
            edge_types = {r[0]: r[1] for r in conn.execute("SELECT edge_type, COUNT(*) FROM graph_edges GROUP BY edge_type").fetchall()}
            node_types = {r[0]: r[1] for r in conn.execute("SELECT source_type, COUNT(*) FROM graph_nodes GROUP BY source_type").fetchall()}
            return {"nodes": node_count, "edges": edge_count, "edge_types": edge_types, "node_types": node_types}
        finally:
            conn.close()

    @mcp.tool
    def memory_graph_save(
        node_type: str,
        node_id: str,
        properties: Dict,
        searchable_text: str,
        content_type: str = "tool",
    ) -> Dict:
        """Speichert einen Node im Graph + VectorStore mit content_type (z.B. für Tool Selector)."""
        from vector_store import get_vector_store
        try:
            get_vector_store().add(
                conversation_id="global", content=searchable_text,
                content_type=content_type, metadata=properties,
            )
            return {"result": f"Saved {node_id} as {content_type}", "node_id": node_id, "content_type": content_type}
        except Exception as e:
            return {"error": f"Vector save failed: {e}"}

    @mcp.tool
    def graph_add_node(
        source_type: str,
        content: str,
        conversation_id: str = "daily-protocol",
        confidence: float = 0.85,
        metadata: str = None,
    ) -> Dict:
        """Erstellt einen Graph-Node mit Embedding für semantische Suche."""
        from graph import build_node_with_edges
        from vector_store import get_vector_store
        embedding = None
        try:
            from embedding import get_embedding
            embedding = get_embedding(content)
        except Exception as e:
            print(f"[graph_add_node] Embedding failed (non-critical): {e}")
        node_id = build_node_with_edges(
            source_type=source_type, content=content, embedding=embedding,
            conversation_id=conversation_id, confidence=confidence, weight_boost=0.5,
        )
        try:
            meta_dict = json.loads(metadata) if metadata else None
            get_vector_store().add(
                conversation_id=conversation_id, content=content,
                content_type=source_type, metadata=meta_dict,
            )
        except Exception as e:
            print(f"[graph_add_node] VectorStore add failed (non-critical): {e}")
        return {"structuredContent": {"node_id": node_id, "created": True}}
