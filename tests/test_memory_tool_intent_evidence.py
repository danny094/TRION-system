"""P11-SP8-R5: exact memory-context evidence declaration."""
import json
from pathlib import Path

from core.orchestrator.tool_descriptor_projection import descriptor_from_raw
from mcp.installer_tool_intents import build_tool_intent_mirror


SOURCE = Path("memory/memory_mcp/tool_intents.json")
POSITIVE = {
    "memory_fact_load",
    "memory_recent",
    "memory_search",
    "memory_search_layered",
    "memory_search_fts",
    "memory_graph_search",
    "memory_graph_neighbors",
    "memory_semantic_search",
}
NEGATIVE = {
    "memory_save",
    "memory_fact_save",
    "memory_autosave_hook",
    "memory_graph_stats",
    "memory_graph_save",
    "graph_add_node",
    "graph_find_duplicate_nodes",
    "graph_merge_nodes",
    "graph_delete_orphan_nodes",
    "graph_prune_weak_edges",
    "memory_semantic_save",
    "memory_embedding_version_status",
    "memory_embedding_backfill",
}


def _payload() -> dict:
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def test_memory_context_positive_and_negative_sets_are_exact() -> None:
    tools = {
        item["name"]: item
        for item in _payload()["tools"]
        if item.get("domain") == "memory"
    }

    assert set(tools) == POSITIVE | NEGATIVE
    assert {
        name
        for name, item in tools.items()
        if item.get("evidence_types") == ["memory_context"]
    } == POSITIVE
    assert all("memory_context" not in item.get("evidence_types", []) for name, item in tools.items() if name in NEGATIVE)


def test_memory_context_survives_mirror_and_descriptor_projection(tmp_path) -> None:
    source = tmp_path / "tool_intents.json"
    source.write_text(json.dumps(_payload()), encoding="utf-8")
    mirror = build_tool_intent_mirror(source, "1.0.0")

    projected = {}
    for intent in mirror["tools"]:
        descriptor = descriptor_from_raw(
            {
                "name": intent["name"],
                "description": intent["description"],
                "mcp": "memory-mcp",
                "inputSchema": {"type": "object"},
                "tool_intent": intent,
            }
        )
        assert descriptor is not None
        projected[intent["name"]] = descriptor.capability_evidence_types

    assert {name for name, evidence in projected.items() if evidence == ["memory_context"]} == POSITIVE
