from typing import Dict, List


def register_graph_admin_tools(mcp) -> None:

    @mcp.tool
    def graph_find_duplicate_nodes() -> Dict:
        """Findet doppelte Nodes im Graph (gleicher Inhalt)."""
        from collections import defaultdict
        from graph import get_graph_store
        try:
            gs = get_graph_store()
            all_nodes = gs.get_nodes_by_type("fact", limit=1000)
            content_map = defaultdict(list)
            for node in all_nodes:
                content = node.get("content", "").strip().lower()
                if content:
                    content_map[content].append(node["id"])
            duplicates = [
                {"content_preview": c[:100], "node_ids": ids, "count": len(ids)}
                for c, ids in content_map.items() if len(ids) > 1
            ]
            return {"structuredContent": {"duplicate_groups": duplicates, "total_duplicates": sum(d["count"] - 1 for d in duplicates)}}
        except Exception as e:
            return {"error": str(e), "duplicate_groups": []}

    @mcp.tool
    def graph_merge_nodes(node_ids: List[int]) -> Dict:
        """Merged mehrere doppelte Nodes in einen (behalte ersten, lösche Rest)."""
        from graph import get_graph_store
        try:
            if len(node_ids) < 2:
                return {"error": "Need at least 2 nodes to merge"}
            gs = get_graph_store()
            primary_id = node_ids[0]
            for node_id in node_ids[1:]:
                for edge in gs.get_edges(node_id):
                    if edge["source"] == node_id:
                        gs.add_edge(src_node_id=primary_id, dst_node_id=edge["target"], edge_type=edge["type"], weight=edge.get("weight", 1.0))
                    elif edge["target"] == node_id:
                        gs.add_edge(src_node_id=edge["source"], dst_node_id=primary_id, edge_type=edge["type"], weight=edge.get("weight", 1.0))
                gs.delete_node(node_id)
            return {"structuredContent": {"merged": len(node_ids) - 1, "primary_node": primary_id, "deleted_nodes": node_ids[1:]}}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool
    def graph_delete_orphan_nodes() -> Dict:
        """Findet und löscht Nodes ohne Edges."""
        from graph import get_graph_store
        try:
            gs = get_graph_store()
            orphans = []
            for node in gs.get_nodes_by_type("fact", limit=1000):
                if not gs.get_edges(node["id"]):
                    orphans.append(node["id"])
                    gs.delete_node(node["id"])
            return {"structuredContent": {"deleted": len(orphans), "orphan_ids": orphans}}
        except Exception as e:
            return {"error": str(e), "deleted": 0}

    @mcp.tool
    def graph_prune_weak_edges(threshold: float = 0.3) -> Dict:
        """Entfernt Edges mit Gewicht unterhalb des Schwellenwerts."""
        from graph import get_graph_store
        try:
            gs = get_graph_store()
            pruned_count = 0
            for node in gs.get_nodes_by_type("fact", limit=1000):
                for edge in gs.get_edges(node["id"]):
                    if edge.get("weight", 1.0) < threshold:
                        gs.delete_edge(edge["source"], edge["target"], edge["type"])
                        pruned_count += 1
            return {"structuredContent": {"pruned": pruned_count, "threshold": threshold}}
        except Exception as e:
            return {"error": str(e), "pruned": 0}
