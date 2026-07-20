"""P11 SP3-E - Beweis: vollstaendige v2-Tool-Metadaten ueberleben den echten
Weg vom Bundle bis zum ToolDescriptor.

Danny-Auftrag (SP3-E): "Beweisen, dass vollstaendige v2-Tool-Metadaten vom
Bundle/Registry-Mirror bis zum ToolDescriptor erhalten bleiben und nicht durch
unvollstaendige Registry-/Config-Daten ueberschrieben oder verloren gehen."

Read-only-Inventar (SP3-E) zeigte: jede einzelne Stufe (build_tool_intent_mirror,
upsert_registry_entry, mcp.config._load_registry, adapters.tool_runner_bridge,
descriptor_from_raw) hat eigene Tests, aber keiner davon durchlaeuft die echte
Kette mit echten Dateien (Bundle-Datei -> Mirror -> mcp_registry.json ->
Registry-Read -> Bridge -> ToolDescriptor) UND prueft alle 9
P11_CAPABILITY_FIELDS gleichzeitig auf dem Endergebnis. Diese Datei schliesst
genau diese Beweis-Luecke (keine neue Logik, reiner Regressionsbeweis).

Zweite Garantie (gleicher Auftrag, "duerfen nicht ... kaputt-deep-mergen"):
mcp.config._load_registry() deep-merged ausschliesslich den Bootstrap-Eintrag
"memory-mcp" (siehe mcp.config._default_mcps()); jeder andere (installer-
verwaltete) Name hat dort kein Gegenstueck und wird daher nie gemergt, sondern
1:1 aus der Registry-Datei uebernommen - das wird hier per Spy auf
mcp.config._deep_merge() mechanisch nachgewiesen, statt nur aus dem Code
geschlussfolgert zu werden.
"""
from __future__ import annotations

import json

from adapters.tool_runner_bridge import get_available_tools
from core.orchestrator.tool_descriptor_projection import descriptor_from_raw
from mcp.installer_registry import upsert_registry_entry
from mcp.installer_tool_intents import P11_CAPABILITY_FIELDS, build_tool_intent_mirror


def _complete_v2_tool() -> dict:
    return {
        "name": "container_inspect",
        "description": "Inspect a container.",
        "domain": "container_runtime",
        "operation": "inspect",
        "requires": ["container_id_or_name"],
        "evidence_types": ["runtime_metadata"],
        "risk": "read_only",
        "target_scopes": ["runtime_state"],
        "freshness_support": "live_only",
        "tool_role": "primary",
        "output_schema": "mcp_output_schema",
    }


def _bind_registry(monkeypatch, tmp_path):
    registry_path = tmp_path / "mcp_registry.json"
    import mcp.config as mcp_config

    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", registry_path)
    return registry_path


def _install_complete_v2_mcp(monkeypatch, tmp_path, mcp_name="container-commander"):
    bundle_dir = tmp_path / mcp_name
    bundle_dir.mkdir()
    intents_path = bundle_dir / "tool_intents.json"
    intents_path.write_text(
        json.dumps({"schema_version": 2, "tools": [_complete_v2_tool()]}),
        encoding="utf-8",
    )
    mirror = build_tool_intent_mirror(intents_path, bundle_version="2.1.0")
    assert mirror["tools"][0]["capability_complete"] is True  # Testvoraussetzung

    upsert_registry_entry(
        mcp_name,
        {
            "enabled": True,
            "transport": "http",
            "url": f"http://{mcp_name}:8000/mcp",
            "description": "Container Commander",
            "version": "2.1.0",
            "tool_intents": mirror,
        },
    )
    return mirror


def _fake_hub(mcp_name):
    class _Hub:
        def list_tools(self):
            return [{"name": "container_inspect", "description": "Inspect a container (live)."}]

        def get_mcp_for_tool(self, name):
            return mcp_name if name == "container_inspect" else None

    return _Hub()


def test_complete_v2_tool_survives_real_bundle_to_descriptor_chain(monkeypatch, tmp_path):
    mcp_name = "container-commander"
    _bind_registry(monkeypatch, tmp_path)
    _install_complete_v2_mcp(monkeypatch, tmp_path, mcp_name)

    import mcp.hub as hub_module

    monkeypatch.setattr(hub_module, "get_hub", lambda: _fake_hub(mcp_name))

    tools = get_available_tools()
    assert [tool["name"] for tool in tools] == ["container_inspect"]

    descriptor = descriptor_from_raw(tools[0])
    assert descriptor is not None

    original = _complete_v2_tool()
    assert descriptor.capability_domain == original["domain"]
    assert descriptor.capability_operation == original["operation"]
    assert descriptor.capability_required_args == original["requires"]
    assert descriptor.capability_evidence_types == original["evidence_types"]
    assert descriptor.capability_risk == original["risk"]
    assert descriptor.capability_target_scopes == original["target_scopes"]
    assert descriptor.capability_freshness_support == original["freshness_support"]
    assert descriptor.tool_role == original["tool_role"]
    assert descriptor.capability_output_schema == original["output_schema"]

    # Gegenbeweis zu P11_CAPABILITY_FIELDS: jedes der 9 Pflichtfelder hat im
    # Bundle einen nicht-leeren Wert UND ist auf dem ToolDescriptor sichtbar
    # (kein Feld wurde auf dem Weg dorthin stillschweigend geleert).
    for field in P11_CAPABILITY_FIELDS:
        assert original[field], f"Testfixture unvollstaendig: {field}"


def test_non_bootstrap_registry_entry_is_never_deep_merged(monkeypatch, tmp_path):
    """Direkter Nachweis am Lese-Layer (mcp.config._load_registry): nur der
    Bootstrap-Name 'memory-mcp' (mcp.config._default_mcps()) kann ueberhaupt
    in den Deep-Merge-Zweig laufen, weil _load_registry() mit genau diesem
    einen Namen als Ausgangsbasis startet. Jeder andere Name hat dort kein
    Gegenstueck und wird 1:1 aus der Datei uebernommen."""
    import mcp.config as mcp_config

    _bind_registry(monkeypatch, tmp_path)
    mirror = _install_complete_v2_mcp(monkeypatch, tmp_path, "container-commander")

    calls = []
    original_deep_merge = mcp_config._deep_merge

    def spy_deep_merge(base, override):
        calls.append((base, override))
        return original_deep_merge(base, override)

    monkeypatch.setattr(mcp_config, "_deep_merge", spy_deep_merge)

    registry = mcp_config.get_all_mcps()

    assert registry["container-commander"]["tool_intents"] == mirror
    # _deep_merge() laeuft legitim fuer "memory-mcp" (Bootstrap-Sonderfall,
    # siehe test_mcp_registry_memory_bootstrap.py) - hier zaehlt nur, dass
    # KEIN Aufruf den installer-verwalteten "container-commander"-Eintrag
    # (erkennbar an registry_entry_from_config()s "managed_by"-Marker) als
    # Override traegt.
    assert not any(override.get("managed_by") == "trion_installer" for _, override in calls)
