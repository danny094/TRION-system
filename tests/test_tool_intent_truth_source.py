"""Phase 2 / Schritt 5 — Regressionssperre gegen Tool-Intent-Mirror.

Pflicht aus docs/45-memory-grounding-fix-plan-2026-05-31:
    Bundle/Manifest-Aenderung muss in available_tool_details sichtbar werden,
    ohne dass eine Python-Konstante angefasst wird.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


def test_mirror_module_is_removed():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("mcp.tool_prompt_hints")


def test_bundle_only_tool_intent_is_not_visible_without_registry_mirror(tmp_path, monkeypatch):
    """P11.0-Zielvertrag: Authoring Source (Bundle) -> Reconcile -> Mirror.
    Ohne Mirror-Eintrag in der Registry darf eine Bundle-Aenderung NICHT sofort
    in available_tool_details sichtbar werden - das waere der verbotene
    Bundle-Fallback im Request-Pfad. Ersetzt den fruheren Test, der genau
    dieses Sofort-Durchschlagen als Sollverhalten gepruft hat.

    P11.0 SP4 Korrektur: Eligibility liegt an der Bridge-Grenze
    (get_available_tools()), nicht erst in descriptor_from_raw(). Ein
    Live-Tool ohne Mirror-Eintrag erscheint deshalb gar nicht erst in der
    zurueckgegebenen Tool-Liste.
    """
    bundle = tmp_path / "synthetic-mcp"
    bundle.mkdir()
    (bundle / "tool_intents.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tools": [
                    {
                        "name": "synthetic_act",
                        "description": "Synthetic tool used to verify mirror truth.",
                        "domain": "synthetic_domain",
                        "operation": "synthetic_op",
                        "supports_entities": ["synthetic_entity"],
                        "evidence_types": ["synthetic_evidence"],
                        "requires": ["synthetic_arg"],
                        "risk": "mutating",
                        "target_scopes": ["synthetic_scope"],
                        "tool_role": "primary",
                        "can_answer_directly": False,
                        "keywords": ["synthetic"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    class _FakeHub:
        def list_tools(self):
            return [{"name": "synthetic_act", "description": "Synthetic"}]

        def get_mcp_for_tool(self, name):
            return "synthetic-mcp" if name == "synthetic_act" else None

    import mcp.hub as hub_module
    import mcp.config as mcp_config

    monkeypatch.setattr(hub_module, "get_hub", lambda: _FakeHub())
    monkeypatch.setattr(
        mcp_config,
        "get_all_mcps",
        lambda: {"synthetic-mcp": {"enabled": True, "cwd": str(bundle)}},
    )

    from adapters.tool_runner_bridge import get_available_tools

    tools = get_available_tools()
    assert tools == []


def test_unknown_tool_has_no_capability_fields_when_mirror_is_silent():
    """P11.0 SP4 (nachgeholte SP0-Zusage): auf den Mirror-Pfad umgeschrieben,
    kein Bundle-/cwd-Fallback mehr. Garantie bleibt: erklaert der
    Registry-Mirror fuer ein Tool keine Capability-Felder, erscheinen sie auch
    nicht im zurueckgegebenen Intent - unabhaengig davon, ob das urspruengliche
    Bundle (Authoring Source) je welche deklariert hat."""

    from adapters.tool_runner_bridge import _tool_intent_for

    intent = _tool_intent_for(
        "container_inspect",
        {
            "tool_intents": {
                "schema_version": 1,
                "tools": [{"name": "container_inspect", "description": "Silent stub."}],
            }
        },
    )
    assert intent["name"] == "container_inspect"
    for forbidden in ("domain", "operation", "risk", "evidence_types", "requires"):
        assert forbidden not in intent


def test_memory_mcp_tool_intents_come_from_json_bundle_file(monkeypatch, tmp_path):
    fake_path = tmp_path / "memory_tool_intents.json"
    fake_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tools": [
                    {
                        "name": "memory_search",
                        "description": "Bundle-defined memory search.",
                        "domain": "memory",
                        "operation": "bundle_op",
                        "risk": "read_only",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    import mcp.config as mcp_config

    monkeypatch.setattr(mcp_config, "_MEMORY_TOOL_INTENTS_PATH", fake_path)
    missing_registry = tmp_path / "missing_registry.json"
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", missing_registry)

    payload = mcp_config.get_all_mcps()

    tools = payload["memory-mcp"]["tool_intents"]["tools"]
    names = [tool["name"] for tool in tools]
    assert names == ["memory_search"]
    assert tools[0]["operation"] == "bundle_op"


def test_shipped_memory_tool_intents_file_provides_known_tools():
    import mcp.config as mcp_config

    payload = mcp_config._load_memory_tool_intents("1.0.0")
    tools = payload.get("tools") or []
    names = {tool.get("name") for tool in tools}
    # The shipped file is the live truth — these are the tools the audit knew about.
    assert {"memory_save", "memory_search", "memory_semantic_search", "graph_find_duplicate_nodes"} <= names


def test_shipped_memory_tool_intents_file_is_in_repo():
    import mcp.config as mcp_config

    assert Path(mcp_config._MEMORY_TOOL_INTENTS_PATH).exists()
