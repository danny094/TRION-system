import json

import pytest

from mcp.installer_common import InstallationError
from mcp.installer_tool_intents import build_tool_intent_mirror, canonical_json_sha256

def _write(tmp_path, payload):
    path = tmp_path / "tool_intents.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path

def _complete_v2_tool(name="container_inspect"):
    return {
        "name": name,
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

def test_build_tool_intent_mirror_includes_header_fields(tmp_path):
    path = _write(tmp_path, {"schema_version": 2, "tools": [_complete_v2_tool()]})

    mirror = build_tool_intent_mirror(path, bundle_version="2.1.0")

    assert mirror["schema_version"] == 2
    assert mirror["bundle_version"] == "2.1.0"
    assert isinstance(mirror["source_sha256"], str) and len(mirror["source_sha256"]) == 64

def test_build_tool_intent_mirror_hash_is_deterministic_regardless_of_key_order(tmp_path):
    payload_a = {"schema_version": 1, "tools": [{"name": "time_now", "description": "Return time."}]}
    payload_b = {"tools": [{"description": "Return time.", "name": "time_now"}], "schema_version": 1}
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    mirror_a = build_tool_intent_mirror(_write(dir_a, payload_a), bundle_version="1.0.0")
    mirror_b = build_tool_intent_mirror(_write(dir_b, payload_b), bundle_version="1.0.0")

    assert mirror_a["source_sha256"] == mirror_b["source_sha256"]

def test_build_tool_intent_mirror_hash_changes_when_content_changes(tmp_path):
    path = _write(tmp_path, {"schema_version": 1, "tools": [{"name": "time_now", "description": "Return time."}]})
    mirror_before = build_tool_intent_mirror(path, bundle_version="1.0.0")

    path.write_text(
        json.dumps({"schema_version": 1, "tools": [{"name": "time_now", "description": "Return the current time."}]}),
        encoding="utf-8",
    )
    mirror_after = build_tool_intent_mirror(path, bundle_version="1.0.0")

    assert mirror_before["source_sha256"] != mirror_after["source_sha256"]

def test_build_tool_intent_mirror_rejects_duplicate_tool_names(tmp_path):
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "tools": [
                {"name": "time_now", "description": "Return time."},
                {"name": "time_now", "description": "Duplicate."},
            ],
        },
    )

    with pytest.raises(InstallationError, match="Duplicate tool name"):
        build_tool_intent_mirror(path, bundle_version="1.0.0")

def test_build_tool_intent_mirror_marks_incomplete_v2_tool_fail_closed(tmp_path):
    incomplete = _complete_v2_tool()
    del incomplete["output_schema"]
    del incomplete["risk"]
    path = _write(tmp_path, {"schema_version": 2, "tools": [incomplete]})

    mirror = build_tool_intent_mirror(path, bundle_version="2.1.0")
    tool = mirror["tools"][0]

    assert tool["capability_complete"] is False
    assert set(tool["missing_capability_fields"]) == {"output_schema", "risk"}

def test_build_tool_intent_mirror_empty_requires_is_not_missing(tmp_path):
    # requires: [] (parameterlose Operation) ist vorhanden, nicht fehlend.
    tool = _complete_v2_tool()
    tool["requires"] = []
    path = _write(tmp_path, {"schema_version": 2, "tools": [tool]})

    mirror = build_tool_intent_mirror(path, bundle_version="2.1.0")
    projected = mirror["tools"][0]

    assert projected["capability_complete"] is True
    assert "missing_capability_fields" not in projected
    assert projected["requires"] == []

def test_build_tool_intent_mirror_missing_requires_key_is_flagged(tmp_path):
    # Gegenstueck: fehlt der Key komplett, bleibt es ein fehlendes Pflichtfeld.
    tool = _complete_v2_tool()
    del tool["requires"]
    path = _write(tmp_path, {"schema_version": 2, "tools": [tool]})

    mirror = build_tool_intent_mirror(path, bundle_version="2.1.0")
    projected = mirror["tools"][0]

    assert projected["capability_complete"] is False
    assert "requires" in projected["missing_capability_fields"]

def test_build_tool_intent_mirror_rejects_embedded_output_schema_object(tmp_path):
    # Eingebettetes Schema-Objekt verstoesst gegen "referenzieren statt
    # duplizieren" - klarer Fehler statt per str() zerstoerter Bezeichner.
    tool = _complete_v2_tool()
    tool["output_schema"] = {"type": "object", "properties": {}}
    path = _write(tmp_path, {"schema_version": 2, "tools": [tool]})

    with pytest.raises(InstallationError, match="output_schema"):
        build_tool_intent_mirror(path, bundle_version="2.1.0")

def test_build_tool_intent_mirror_rejects_arbitrary_output_schema_identifier(tmp_path):
    # In Schema v2 ist `mcp_output_schema` der einzige gueltige Wert -
    # ein beliebiger String wie "container_inspect_v1" ist keine Referenz.
    tool = _complete_v2_tool()
    tool["output_schema"] = "container_inspect_v1"
    path = _write(tmp_path, {"schema_version": 2, "tools": [tool]})

    with pytest.raises(InstallationError, match="output_schema"):
        build_tool_intent_mirror(path, bundle_version="2.1.0")

def test_build_tool_intent_mirror_v1_tolerates_arbitrary_output_schema_string(tmp_path):
    # Der mcp_output_schema-Sentinel gilt nur ab v2 - v1 bleibt tolerant.
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "tools": [{"name": "time_now", "description": "Return time.", "output_schema": "container_inspect_v1"}],
        },
    )

    mirror = build_tool_intent_mirror(path, bundle_version="1.0.0")

    assert mirror["tools"][0]["output_schema"] == "container_inspect_v1"

def test_build_tool_intent_mirror_rejects_unsupported_schema_version(tmp_path):
    path = _write(tmp_path, {"schema_version": 3, "tools": [_complete_v2_tool()]})

    with pytest.raises(InstallationError, match="schema_version"):
        build_tool_intent_mirror(path, bundle_version="2.1.0")

def test_build_tool_intent_mirror_rejects_empty_bundle_version(tmp_path):
    path = _write(tmp_path, {"schema_version": 2, "tools": [_complete_v2_tool()]})

    with pytest.raises(InstallationError, match="bundle_version"):
        build_tool_intent_mirror(path, bundle_version="   ")

def test_build_tool_intent_mirror_v2_complete_tool_has_no_missing_fields(tmp_path):
    path = _write(tmp_path, {"schema_version": 2, "tools": [_complete_v2_tool()]})

    mirror = build_tool_intent_mirror(path, bundle_version="2.1.0")
    tool = mirror["tools"][0]

    assert tool["capability_complete"] is True
    assert "missing_capability_fields" not in tool

def test_build_tool_intent_mirror_legacy_v1_tools_are_not_fail_closed_marked(tmp_path):
    path = _write(
        tmp_path,
        {"schema_version": 1, "tools": [{"name": "time_now", "description": "Return time."}]},
    )

    mirror = build_tool_intent_mirror(path, bundle_version="1.0.0")
    tool = mirror["tools"][0]

    assert "capability_complete" not in tool
    assert "missing_capability_fields" not in tool

def test_build_tool_intent_mirror_denormalizes_tool_intent_meta_per_tool(tmp_path):
    path = _write(tmp_path, {"schema_version": 2, "tools": [_complete_v2_tool()]})

    mirror = build_tool_intent_mirror(path, bundle_version="2.1.0")
    tool = mirror["tools"][0]

    assert tool["tool_intent_meta"] == {
        "schema_version": 2,
        "source_sha256": mirror["source_sha256"],
        "bundle_version": "2.1.0",
    }

def test_canonical_json_sha256_is_order_insensitive():
    assert canonical_json_sha256({"a": 1, "b": 2}) == canonical_json_sha256({"b": 2, "a": 1})
