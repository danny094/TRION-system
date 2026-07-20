import json

from adapters.tool_runner_bridge import _tool_intent_for


def test_tool_intent_for_prefers_registry_tool_intents_when_present(tmp_path):
    bundle = tmp_path / "time-mcp"
    bundle.mkdir()
    (bundle / "tool_intents.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tools": [{"name": "time_now", "description": "Bundle intent"}],
            }
        ),
        encoding="utf-8",
    )

    intent = _tool_intent_for(
        "time_now",
        {
            "cwd": str(bundle),
            "tool_intents": {
                "schema_version": 1,
                "tools": [{"name": "time_now", "description": "Registry intent"}],
            },
        },
    )

    assert intent["description"] == "Registry intent"


def test_tool_intent_for_returns_empty_when_no_registry_mirror_present(tmp_path):
    """P11.0-Zielvertrag: kein Bundle-Fallback im Request-Pfad. Fehlt der
    Registry-Mirror (config ohne 'tool_intents'), liefert _tool_intent_for()
    kein Intent zurueck - auch wenn das Bundle selbst ein vollstaendiges,
    gueltiges tool_intents.json mit Capability-Feldern enthaelt.
    """
    bundle = tmp_path / "container-commander"
    bundle.mkdir()
    (bundle / "tool_intents.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tools": [
                    {
                        "name": "container_inspect",
                        "description": "Inspect a container",
                        "domain": "container_runtime",
                        "operation": "inspect",
                        "supports_entities": ["container"],
                        "evidence_types": ["runtime_metadata", "home_scope"],
                        "requires": ["container_id_or_name"],
                        "risk": "read_only",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    intent = _tool_intent_for("container_inspect", {"cwd": str(bundle)})

    assert intent == {}


def test_tool_intent_for_returns_only_what_registry_mirror_declares():
    """Guarantee re-scoped from the removed bundle-fallback test to the
    registry/mirror path: _tool_intent_for() must not add fields beyond what
    the registry's tool_intents entry declares."""
    intent = _tool_intent_for(
        "container_inspect",
        {
            "tool_intents": {
                "schema_version": 1,
                "tools": [{"name": "container_inspect", "description": "Inspect a container"}],
            }
        },
    )

    assert intent["name"] == "container_inspect"
    assert intent["description"] == "Inspect a container"
    for forbidden in ("domain", "operation", "risk", "evidence_types", "requires"):
        assert forbidden not in intent


def test_tool_intent_for_passes_through_capability_fields_declared_in_registry_mirror():
    """Guarantee re-scoped from the removed bundle-fallback test to the
    registry/mirror path: capability fields declared in the registry's
    tool_intents entry must fully reach the runtime path."""
    intent = _tool_intent_for(
        "container_inspect",
        {
            "tool_intents": {
                "schema_version": 1,
                "tools": [
                    {
                        "name": "container_inspect",
                        "description": "Inspect a container",
                        "domain": "container_runtime",
                        "operation": "inspect",
                        "supports_entities": ["container"],
                        "evidence_types": ["runtime_metadata", "home_scope"],
                        "requires": ["container_id_or_name"],
                        "risk": "read_only",
                    }
                ],
            }
        },
    )

    assert intent["domain"] == "container_runtime"
    assert intent["operation"] == "inspect"
    assert intent["evidence_types"] == ["runtime_metadata", "home_scope"]
    assert intent["requires"] == ["container_id_or_name"]
    assert intent["risk"] == "read_only"
