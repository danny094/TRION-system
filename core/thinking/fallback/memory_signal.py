"""Memory-signal keyword vocabulary and detection for the fallback analyzer.

Single home for the keyword tuples that decide whether a user message
carries a memory-related signal (history/project context, memory items present).

Moved to intelligence_modules as part of PIANO 1.0:
- Tool-selection keywords (CONTAINER_KW, SAVE_KW, RECALL_KW) →
  intelligence_modules/cim_skill_rag/tool_selection_rules.csv (Schritt 3.1, 2026-06-11)
- Memory-block keywords (MEMORY_ANALYSIS_KW, VAGUE_MEMORY_SEARCH_KW) →
  intelligence_modules/cim_skill_rag/memory_block_signals.csv (B3-Fix, 2026-06-11)
"""

from __future__ import annotations

from typing import Any, Mapping

MEMORY_KW = ("erinner", "remember", "gemerkt", "projekt", "project")
PROJECT_KW = ("projekt", "project")
HISTORY_KW = ("vorhin", "gestern", "earlier", "wie besprochen")


def has_memory_items(orchestrator_context: Mapping[str, Any] | None) -> bool:
    if not isinstance(orchestrator_context, Mapping):
        return False
    inner = orchestrator_context.get("context") if "context" in orchestrator_context else orchestrator_context
    memory = inner.get("memory") if isinstance(inner, Mapping) else None
    items = memory.get("items") if isinstance(memory, Mapping) else None
    return isinstance(items, list) and bool(items)
