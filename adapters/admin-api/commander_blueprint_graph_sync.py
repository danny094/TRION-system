from __future__ import annotations

import json
import logging
from datetime import datetime

from commander_deploy_blueprints import ensure_store_initialized, list_blueprints
from commander_blueprint_trust import evaluate_blueprint_trust


logger = logging.getLogger(__name__)


def sync_blueprint_to_graph(bp, trust_level: str = "", force_update: bool = False) -> bool:
    ensure_store_initialized()
    try:
        from mcp.client import call_tool

        if not force_update:
            existing_raw = call_tool(
                "memory_graph_search",
                {"conversation_id": "_blueprints", "query": bp.id, "limit": 5},
            ) or {}
            existing = existing_raw.get("result", existing_raw) if isinstance(existing_raw, dict) else {}
            structured = (
                existing_raw.get("structuredContent", {}) or existing.get("structuredContent", {})
            ) if isinstance(existing_raw, dict) else {}
            nodes = existing.get("nodes") or existing.get("results") or structured.get("nodes") or structured.get("results") or []
            for node in nodes:
                try:
                    metadata_raw = node.get("metadata") or "{}"
                    metadata = metadata_raw if isinstance(metadata_raw, dict) else json.loads(metadata_raw)
                except Exception:
                    continue
                if metadata.get("blueprint_id") == bp.id:
                    logger.info("[CommanderBlueprintGraphSync] %s already in graph — skipping", bp.id)
                    return True

        if not trust_level:
            try:
                trust_level = evaluate_blueprint_trust(bp)["level"]
            except Exception:
                trust_level = "unverified"

        caps = bp.tags or []
        result = call_tool(
            "graph_add_node",
            {
                "conversation_id": "_blueprints",
                "source_type": "blueprint",
                "content": f"{bp.id}: {bp.description or bp.name} (Capabilities: {', '.join(caps)})",
                "confidence": 0.9,
                "metadata": json.dumps(
                    {
                        "blueprint_id": bp.id,
                        "name": bp.name,
                        "trust_level": trust_level,
                        "capabilities": caps,
                        "network": bp.network.value if bp.network else "internal",
                        "image": bp.image or "",
                        "memory": bp.resources.memory_limit if bp.resources else "",
                        "cpu": bp.resources.cpu_limit if bp.resources else "",
                        "updated_at": bp.updated_at or "",
                    }
                ),
            },
        )
        if result and result.get("error"):
            logger.warning("[CommanderBlueprintGraphSync] graph_add_node error for %s: %s", bp.id, result)
            return False
        logger.info("[CommanderBlueprintGraphSync] Synced %s (trust=%s)", bp.id, trust_level)
        return True
    except Exception as exc:
        logger.warning("[CommanderBlueprintGraphSync] sync_blueprint_to_graph failed for %s: %s", bp.id, exc)
        return False


def remove_blueprint_from_graph(blueprint_id: str) -> int:
    ensure_store_initialized()
    try:
        from mcp.client import call_tool

        existing_raw = call_tool(
            "memory_graph_search",
            {"conversation_id": "_blueprints", "query": blueprint_id, "limit": 10},
        ) or {}
        existing = existing_raw.get("result", existing_raw) if isinstance(existing_raw, dict) else {}
        structured = (
            existing_raw.get("structuredContent", {}) or existing.get("structuredContent", {})
        ) if isinstance(existing_raw, dict) else {}
        nodes = existing.get("nodes") or existing.get("results") or structured.get("nodes") or structured.get("results") or []

        marked = 0
        for node in nodes:
            try:
                metadata_raw = node.get("metadata") or "{}"
                metadata = metadata_raw if isinstance(metadata_raw, dict) else json.loads(metadata_raw)
            except Exception:
                continue
            if metadata.get("blueprint_id") != blueprint_id:
                continue
            metadata["is_deleted"] = True
            metadata["deleted_at"] = datetime.utcnow().isoformat()
            call_tool(
                "graph_add_node",
                {
                    "conversation_id": "_blueprints",
                    "source_type": "blueprint",
                    "content": node.get("content", blueprint_id),
                    "confidence": 0.0,
                    "metadata": json.dumps(metadata),
                },
            )
            marked += 1
        return marked
    except Exception as exc:
        logger.warning("[CommanderBlueprintGraphSync] remove_blueprint_from_graph failed for %s: %s", blueprint_id, exc)
        return 0


def sync_blueprints_to_graph() -> int:
    ensure_store_initialized()
    try:
        from mcp.client import call_tool
    except ImportError as exc:
        logger.error("[CommanderBlueprintGraphSync] Cannot import mcp.client: %s", exc)
        return 0

    blueprints = list_blueprints()
    if not blueprints:
        return 0

    existing_ids: set[str] = set()
    try:
        response = call_tool(
            "memory_graph_search",
            {"query": "blueprint", "conversation_id": "_blueprints", "depth": 0, "limit": 100},
        )
        result = response.get("result", response) if response else {}
        for node in (result.get("results", []) if isinstance(result, dict) else []):
            try:
                metadata_raw = node.get("metadata") or "{}"
                metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
                blueprint_id = metadata.get("blueprint_id")
                if blueprint_id:
                    existing_ids.add(blueprint_id)
            except Exception:
                pass
        logger.info("[CommanderBlueprintGraphSync] %s blueprints already in graph", len(existing_ids))
    except Exception as exc:
        logger.warning("[CommanderBlueprintGraphSync] Could not fetch existing graph nodes: %s — syncing all", exc)

    count = 0
    for bp in blueprints:
        if bp.id in existing_ids:
            continue
        if sync_blueprint_to_graph(bp):
            count += 1

    logger.info("[CommanderBlueprintGraphSync] Done: %s new blueprints synced", count)
    return count
