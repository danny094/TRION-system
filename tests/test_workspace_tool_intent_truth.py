"""P11-SP8-R5: live Workspace signatures and authoring truth stay aligned."""
import ast
import json
from pathlib import Path

from core.orchestrator.tool_descriptor_projection import descriptor_from_raw
from mcp.installer_tool_intents import build_tool_intent_mirror


SOURCE = Path("memory/memory_mcp/tool_intents.json")
LIVE_SOURCE = Path("memory/memory_mcp/tool_groups/workspace_tools.py")
EXPECTED = {
    "workspace_save": ("write", "mutating", [], ["conversation_id", "content"], "primary", False),
    "workspace_list": ("list", "read_only", ["file_context"], [], "primary", True),
    "workspace_get": ("read", "read_only", ["file_context"], ["entry_id"], "primary", True),
    "workspace_update": ("update", "mutating", [], ["entry_id", "content"], "primary", False),
    "workspace_delete": ("delete", "mutating", [], ["entry_id"], "forbidden_direct", False),
}


def _required_arguments() -> dict[str, list[str]]:
    tree = ast.parse(LIVE_SOURCE.read_text(encoding="utf-8"))
    required = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in EXPECTED:
            continue
        positional = [argument.arg for argument in node.args.args]
        required_count = len(positional) - len(node.args.defaults)
        required[node.name] = positional[:required_count]
    return required


def _workspace_intents() -> dict[str, dict]:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    return {item["name"]: item for item in payload["tools"] if item["name"].startswith("workspace_")}


def test_workspace_authoring_contract_matches_all_five_live_signatures() -> None:
    intents = _workspace_intents()
    required = _required_arguments()

    assert set(required) == set(EXPECTED)
    assert set(intents) == set(EXPECTED)
    for name, (operation, risk, evidence, requires, role, direct) in EXPECTED.items():
        intent = intents[name]
        assert intent["domain"] == "files"
        assert intent["operation"] == operation
        assert intent["risk"] == risk
        assert intent["target_scopes"] == ["project_docs"]
        assert intent.get("evidence_types", []) == evidence
        assert intent["requires"] == requires == required[name]
        assert intent["tool_role"] == role
        assert intent["can_answer_directly"] is direct


def test_workspace_contract_survives_mirror_and_descriptor_projection(tmp_path) -> None:
    source = tmp_path / "tool_intents.json"
    source.write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    mirror = build_tool_intent_mirror(source, "1.0.0")
    intents = {item["name"]: item for item in mirror["tools"] if item["name"].startswith("workspace_")}

    assert set(intents) == set(EXPECTED)
    for name, intent in intents.items():
        descriptor = descriptor_from_raw(
            {
                "name": name,
                "description": intent["description"],
                "mcp": "memory-mcp",
                "inputSchema": {"type": "object"},
                "tool_intent": intent,
            }
        )
        assert descriptor is not None
        assert descriptor.capability_domain == "files"
        assert descriptor.capability_operation == EXPECTED[name][0]
        assert descriptor.capability_evidence_types == EXPECTED[name][2]
        assert descriptor.capability_target_scopes == ["project_docs"]
