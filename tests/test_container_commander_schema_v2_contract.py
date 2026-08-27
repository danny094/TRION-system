import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "mcp-servers" / "container-commander"
BUNDLE_ROOT = ROOT / "examples" / "container_commander_bundle"
SCRIPTS_ROOT = ROOT / "scripts"
if str(BUNDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(BUNDLE_ROOT))
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import bundle_dispatch  # noqa: E402
from container_commander_bundle_gen.source_ast import load_context  # noqa: E402


CAPABILITY_FIELDS = {
    "domain",
    "operation",
    "requires",
    "evidence_types",
    "risk",
    "target_scopes",
    "freshness_support",
    "tool_role",
    "output_schema",
}


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_source_contracts_bind_all_tools_to_schema_v2(tmp_path):
    intents_path = SOURCE_ROOT / "tool_intents.json"
    schemas_path = SOURCE_ROOT / "output_schemas.json"
    assert intents_path.is_file()
    assert schemas_path.is_file()

    context = load_context(ROOT, tmp_path / "bundle")
    source_names = [tool.name for module in context.modules for tool in module.tools]
    intents = _json(intents_path)
    schemas = _json(schemas_path)
    intent_names = [tool["name"] for tool in intents["tools"]]

    assert len(source_names) == 46
    assert intents["schema_version"] == 2
    assert intent_names == source_names
    assert set(schemas) == set(source_names)
    assert len(schemas) == 46
    for tool in intents["tools"]:
        assert CAPABILITY_FIELDS <= tool.keys()
        assert tool["target_scopes"] == ["runtime_state"]
        assert tool["freshness_support"] == "live_only"
        assert tool["tool_role"] == "primary"
        assert tool["output_schema"] == "mcp_output_schema"
        assert "outputSchema" not in tool


def test_generated_bundle_projects_source_intents_and_output_schemas():
    source_intents = _json(SOURCE_ROOT / "tool_intents.json")
    bundle_intents = _json(BUNDLE_ROOT / "tool_intents.json")
    schemas = _json(SOURCE_ROOT / "output_schemas.json")
    live_tools = {tool["name"]: tool for tool in bundle_dispatch.TOOLS}

    assert bundle_intents == source_intents
    assert set(live_tools) == set(schemas)
    for name, schema in schemas.items():
        assert live_tools[name]["outputSchema"] == schema
