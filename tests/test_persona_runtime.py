from pathlib import Path

from core import persona as persona_module
from core.output import persona_runtime


def _persona_text(name: str) -> str:
    return f"[IDENTITY]\nname: {name}\nrole: Test Persona\n"


def _patch_rules(monkeypatch, rules):
    monkeypatch.setattr(persona_runtime, "load_persona_capability_rules", lambda: rules)


def test_dynamic_context_activates_capability_from_available_tool_details(monkeypatch):
    # P11.0 SP4: Quelle ist available_tool_details (ToolDescriptor-Projektion,
    # bereits Live-Discovery INTERSECT Registry Mirror gefiltert), nicht mehr
    # die wirkungslose available_tools-Namensliste.
    _patch_rules(monkeypatch, {"can_inspect_containers": [("domain_eq", "container_runtime")]})
    context = {
        "orchestrator": {
            "available_tools": ["container_inspect"],
            "available_tool_details": [
                {"name": "container_inspect", "description": "Inspect a container.", "capability_domain": "container_runtime"}
            ],
        }
    }

    result = persona_runtime._dynamic_context(context)

    assert result == {"capabilities": {"can_inspect_containers": True}}


def test_dynamic_context_ignores_legacy_available_tools_name_strings(monkeypatch):
    # Regressionssperre gegen den urspruenglichen Fund: available_tools ist
    # eine reine Namensliste (Strings) und darf nie wieder als Metadatenquelle
    # gelesen werden, auch wenn sie zufaellig nicht leer ist.
    _patch_rules(monkeypatch, {"can_inspect_containers": [("name_contains", "container_inspect")]})
    context = {
        "orchestrator": {
            "available_tools": ["container_inspect"],
            "available_tool_details": [],
        }
    }

    result = persona_runtime._dynamic_context(context)

    assert result == {}


def test_dynamic_context_returns_empty_when_no_tool_matches_any_rule(monkeypatch):
    _patch_rules(monkeypatch, {"can_inspect_containers": [("domain_eq", "container_runtime")]})
    context = {
        "orchestrator": {
            "available_tool_details": [
                {"name": "memory_search", "description": "Search memory.", "capability_domain": "memory"}
            ],
        }
    }

    result = persona_runtime._dynamic_context(context)

    assert result == {}


def test_dynamic_context_returns_empty_when_orchestrator_context_missing():
    assert persona_runtime._dynamic_context({}) == {}
    assert persona_runtime._dynamic_context({"orchestrator": "not-a-dict"}) == {}


def test_save_active_persona_invalidates_cached_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(persona_module, "PERSONAS_DIR", tmp_path)
    monkeypatch.setattr(persona_module, "_active_persona_name", "default")
    monkeypatch.setattr(persona_module, "_persona_instance", None)

    default_path = Path(tmp_path) / "default.txt"
    default_path.write_text(_persona_text("Alpha"), encoding="utf-8")

    loaded = persona_module.load_persona("default")
    assert loaded.name == "Alpha"

    saved = persona_module.save_persona("default", _persona_text("Beta"))
    assert saved is True
    assert persona_module._persona_instance is None

    reloaded = persona_module.get_persona()
    assert reloaded.name == "Beta"
