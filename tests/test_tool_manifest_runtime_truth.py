"""P11.0 SP4 - Mirror-only Runtime: Live-Discovery INTERSECT Registry Mirror.

Bindender Zielvertrag (p11-0-tool-manifest-registry-mirror.md):
    Runtime-Eligibility entsteht nur aus Live MCP Tooldefinition INTERSECT
    Registry Mirror. Ein Tool ohne Live-Definition oder gueltigen
    Mirror-Eintrag ist nicht ausfuehrbar.

P11.0 SP4 Korrektur (Round 2): Eligibility ist eine gemeinsame Predicate-
Funktion - core/orchestrator/tool_descriptor_projection.py::is_eligible_tool_intent().
adapters.tool_runner_bridge.get_available_tools() ist der primaere
Chokepoint: Live-Tools ohne gueltigen Mirror-Eintrag (fehlende/unvollstaendige/
typfalsche `tool_intent_meta`, unbekannte `schema_version`, ungueltiger
Hash/Bundle-Version) oder mit einem Schema-v2-Eintrag ohne exakt
`capability_complete is True` (fehlend, `False` oder sonstiger Wert)
erscheinen dort gar nicht erst in orchestrator_raw_tools - siehe
tests/test_tool_intent_truth_source.py und tests/test_tool_runner_bridge.py.
core/orchestrator/tool_descriptor_projection.py::descriptor_from_raw() ruft
dieselbe Predicate-Funktion zusaetzlich als Fail-closed-Guard auf jedem
Eingang auf, unabhaengig davon ob er die Bridge durchlaufen hat: ein Tool
ohne gueltigen Mirror-Eintrag liefert dort None und taucht in
list_available_tools() (core/orchestrator/tools.py) nicht mehr auf.

Zusaetzlich: das Memory Knowledge Graph (mcp/registry.py) ist ein
schreibender, niemals lesender Konsument der Live-Discovery (mcp/hub.py
_register_tools_in_memory()) und darf Eligibility nicht beeinflussen - ein
Totalausfall der Registrierung darf die Live-Tool-Caches des Hubs nicht
veraendern.
"""

import pytest

from core.orchestrator.tool_descriptor_projection import descriptor_from_raw, is_eligible_tool_intent
from core.orchestrator.tools import list_available_tools

_VALID_V1_META = {"schema_version": 1, "source_sha256": "c" * 64, "bundle_version": "1.0.0"}
_VALID_V2_META = {"schema_version": 2, "source_sha256": "c" * 64, "bundle_version": "2.0.0"}


def _v2_tool_intent(**overrides):
    base = {
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
        "capability_complete": True,
        "tool_intent_meta": {
            "schema_version": 2,
            "source_sha256": "a" * 64,
            "bundle_version": "2.1.0",
        },
    }
    base.update(overrides)
    return base


def test_descriptor_from_raw_excludes_tool_without_any_mirror_entry():
    raw = {"name": "container_inspect", "description": "Live tool, no mirror.", "tool_intent": {}}
    assert descriptor_from_raw(raw) is None


def test_descriptor_from_raw_excludes_tool_missing_tool_intent_key_entirely():
    raw = {"name": "container_inspect", "description": "Live tool, key absent."}
    assert descriptor_from_raw(raw) is None


def test_descriptor_from_raw_excludes_incomplete_v2_tool_marked_capability_incomplete():
    raw = {
        "name": "container_inspect",
        "tool_intent": _v2_tool_intent(capability_complete=False, missing_capability_fields=["risk"]),
    }
    assert descriptor_from_raw(raw) is None


def test_descriptor_from_raw_excludes_tool_intent_with_missing_name():
    raw = {"name": "container_inspect", "tool_intent": _v2_tool_intent(name="")}
    assert descriptor_from_raw(raw) is None


def test_descriptor_from_raw_excludes_mismatched_tool_intent_name():
    # Round 4: ein gueltiger Mirror-Eintrag fuer "harmless_tool" darf nicht
    # als Eligibility-Nachweis fuer "dangerous_tool" durchgehen.
    raw = {"name": "dangerous_tool", "tool_intent": _v2_tool_intent(name="harmless_tool")}
    assert descriptor_from_raw(raw) is None


def test_descriptor_from_raw_includes_legacy_v1_tool_with_minimal_mirror_entry():
    # Legacy v1 trägt kein capability_complete-Marker - bleibt eligible, wenn
    # ueberhaupt ein (auch minimaler) Mirror-Eintrag existiert.
    raw = {
        "name": "time_now",
        "tool_intent": {
            "name": "time_now",
            "description": "Return time.",
            "tool_intent_meta": {"schema_version": 1, "source_sha256": "b" * 64, "bundle_version": "1.0.0"},
        },
    }
    descriptor = descriptor_from_raw(raw)
    assert descriptor is not None
    assert descriptor.name == "time_now"
    assert descriptor.tool_role == "primary"


def test_descriptor_from_raw_populates_mirror_metadata_from_tool_intent_meta():
    raw = {
        "name": "container_inspect",
        "outputSchema": {"type": "object"},
        "tool_intent": _v2_tool_intent(),
    }
    descriptor = descriptor_from_raw(raw)
    assert descriptor is not None
    assert descriptor.mirror_schema_version == 2
    assert descriptor.mirror_source_sha256 == "a" * 64
    assert descriptor.mirror_bundle_version == "2.1.0"
    assert descriptor.capability_domain == "container_runtime"


def test_descriptor_from_raw_projects_output_schema_from_tool_intent():
    """SP3-C-Fund (2026-06-28, Codex-bestaetigt): output_schema wird am
    Registry-Mirror-Gate validiert (capability_complete-Pflichtfeld,
    mcp/installer_tool_intents.py::P11_CAPABILITY_FIELDS), ging aber bisher
    spurlos zwischen Mirror und ToolDescriptor verloren - descriptor_from_raw()
    las das Feld nie aus tool_intent. SP3-D-Fix: muss jetzt projiziert
    werden."""
    raw = {
        "name": "container_inspect",
        "outputSchema": {"type": "object"},
        "tool_intent": _v2_tool_intent(),
    }
    descriptor = descriptor_from_raw(raw)
    assert descriptor is not None
    assert descriptor.capability_output_schema == "mcp_output_schema"


def test_list_available_tools_intersects_live_discovery_with_mirror():
    raw_tools = [
        {
            "name": "container_inspect",
            "outputSchema": {"type": "object"},
            "tool_intent": _v2_tool_intent(),
        },
        {"name": "ghost_tool", "description": "Live, but no mirror entry.", "tool_intent": {}},
    ]
    descriptors = list_available_tools(raw_tools)
    assert [tool.name for tool in descriptors] == ["container_inspect"]


@pytest.mark.parametrize(
    "tool_intent",
    [
        {"name": "x"},  # tool_intent_meta fehlt komplett
        {"name": "x", "tool_intent_meta": {**_VALID_V1_META, "schema_version": True}},  # bool statt int (True == 1)
        {"name": "x", "tool_intent_meta": {**_VALID_V1_META, "schema_version": 1.0}},  # float statt int (1.0 == 1)
        {"name": "x", "tool_intent_meta": {**_VALID_V1_META, "schema_version": 3}},  # unbekannte Schema-Version
        {"name": "x", "tool_intent_meta": {**_VALID_V1_META, "source_sha256": int("1" * 64)}},  # Hash ist int, nicht str
        {"name": "x", "tool_intent_meta": {**_VALID_V1_META, "source_sha256": "z" * 64}},  # Hash kein Hex
        {"name": "x", "tool_intent_meta": {**_VALID_V1_META, "bundle_version": ""}},  # Bundle-Version leer
        {"name": "x", "tool_intent_meta": {**_VALID_V1_META, "bundle_version": {"v": 1}}},  # Bundle-Version kein str
        {"name": "x", "tool_intent_meta": _VALID_V2_META},  # v2 ohne capability_complete-Feld
        {"name": "x", "tool_intent_meta": _VALID_V2_META, "capability_complete": False},  # v2 explizit False
    ],
)
def test_is_eligible_tool_intent_rejects_type_unsafe_or_incomplete_metadata(tool_intent):
    assert is_eligible_tool_intent(tool_intent) is False


def test_is_eligible_tool_intent_accepts_valid_v1_and_v2_metadata():
    assert is_eligible_tool_intent({"name": "x", "tool_intent_meta": _VALID_V1_META}) is True
    assert is_eligible_tool_intent(
        {"name": "x", "tool_intent_meta": _VALID_V2_META, "capability_complete": True}
    ) is True


def test_memory_knowledge_graph_failure_does_not_affect_hub_tool_caches(monkeypatch):
    import mcp.hub as hub_module

    hub = hub_module.MCPHub()
    hub._tool_definitions = {"container_inspect": {"name": "container_inspect"}}
    hub._tools_cache = {"container_inspect": "container-commander"}

    class _BoomRegistry:
        def __init__(self, _hub):
            pass

        def register_all(self):
            raise RuntimeError("knowledge graph is down")

    monkeypatch.setattr("mcp.registry.MCPRegistry", _BoomRegistry)

    hub._register_tools_in_memory()  # darf nicht raisen (siehe except-Block)

    assert hub._tool_definitions == {"container_inspect": {"name": "container_inspect"}}
    assert hub._tools_cache == {"container_inspect": "container-commander"}
