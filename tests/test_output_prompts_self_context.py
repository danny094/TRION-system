from core.output.prompts import build_output_system_prompt
from tests._output_prompts_helpers import plan_answer_user


def test_output_prompt_includes_verified_home_context_for_capability_answers():
    context = {
        "orchestrator": {
            "context": {
                "home_context": {
                    "verified": True,
                    "container_name": "trion-home",
                    "runtime_profile": "trion-home",
                    "home_root": "/home/trion",
                    "available_capability_classes": ["container_inspect", "container_inventory"],
                    "missing_capability_classes": ["file_write", "local_exec"],
                    "allowed_write_roots": ["/home/trion/notes"],
                }
            }
        }
    }

    prompt = build_output_system_prompt(plan_answer_user(), context)
    assert "## Verifizierter Home-/Scope-Kontext" in prompt
    assert "container_name: trion-home" in prompt
    assert "available_capability_classes: container_inspect, container_inventory" in prompt
    assert "missing_capability_classes: file_write, local_exec" in prompt
    assert "container_inventory: laufende oder verfuegbare Container im Runtime-Kontext auflisten" in prompt
    assert "local_exec: lokale Befehle im erlaubten Scope ausfuehren" in prompt


def test_output_prompt_includes_self_context_for_capability_and_visibility_answers():
    context = {
        "orchestrator": {
            "context": {
                "self_context": {
                    "identity": {
                        "name": "TRION",
                        "role": "local_first_ai_os_agent",
                    },
                    "current_scope": {
                        "runtime_profile": "trion-home",
                        "home_container_name": "trion-home",
                    },
                    "memory_visibility": {
                        "memory_mode": "conversation_only",
                        "allow_global_memory_read": False,
                        "allow_long_term_write": False,
                        "max_memory_hits": 5,
                    },
                    "capabilities": [
                        {
                            "name": "memory_read",
                            "status": "verified",
                            "source": "conversation_policy",
                            "description": "kuratierten Memory-Kontext und relevante Erinnerungen lesen",
                        },
                        {
                            "name": "container_inspect",
                            "status": "verified",
                            "source": "home_context",
                            "description": "Container-Metadaten und Runtime-Details pruefen",
                        },
                    ],
                    "uncertainties": [
                        {
                            "subject": "home_scope",
                            "status": "unknown",
                            "message": "Home-Scope ist aktuell nicht verifiziert.",
                        }
                    ],
                }
            }
        }
    }

    prompt = build_output_system_prompt(plan_answer_user(), context)
    assert "## Verifizierter Self-Context" in prompt
    assert "identity: TRION (local_first_ai_os_agent)" in prompt
    assert "memory_visibility: mode=conversation_only, global_read=False, long_term_write=False, max_hits=5" in prompt
    assert "capability_classes (abstrakt, keine Tool-Namen)" in prompt
    assert "class:memory_read [verified via conversation_policy]" in prompt
    assert "class:container_inspect [verified via home_context]" in prompt
    assert "home_scope [unknown]: Home-Scope ist aktuell nicht verifiziert." in prompt
    assert "VERFUEGBARE TOOLS" in prompt


def test_self_context_block_never_renders_raw_tool_names():
    """Anti-drift guard fuer docs/memory-grounding/34-semantic-tool-truth-drift.md.

    Der Self-Context-Block darf nie konkrete Tool-Namen aus der Live-Discovery
    rendern. Capability-Klassen muessen klar als Klassen markiert sein (Praefix
    'class:'). Tool-Namen kommen ausschliesslich aus dem 'VERFUEGBARE TOOLS'-
    Block, der aus mcp/hub.list_tools() gespeist wird.
    """
    raw_live_tool_names = [
        "container_list",
        "container_inspect",
        "container_logs",
        "workspace_get",
        "workspace_save",
        "workspace_update",
        "workspace_list",
        "workspace_delete",
        "memory_save",
        "memory_semantic_search",
        "time_now",
        "start_stopped_container",
        "stop_container",
    ]
    context = {
        "orchestrator": {
            "context": {
                "self_context": {
                    "identity": {"name": "TRION", "role": "local_first_ai_os_agent"},
                    "current_scope": {"runtime_profile": "trion-home"},
                    "memory_visibility": {
                        "memory_mode": "conversation_only",
                        "allow_global_memory_read": False,
                        "allow_long_term_write": True,
                        "max_memory_hits": 5,
                    },
                    "capabilities": [
                        {
                            "name": "container_inventory",
                            "status": "verified",
                            "source": "tool_intent_discovery:1",
                            "description": "laufende oder verfuegbare Container im Runtime-Kontext auflisten",
                        },
                        {
                            "name": "workspace_read",
                            "status": "verified",
                            "source": "tool_intent_discovery:1",
                            "description": "Workspace-Inhalte lesen",
                        },
                    ],
                    "uncertainties": [],
                }
            }
        }
    }
    prompt = build_output_system_prompt(plan_answer_user(), context)

    # Capability-Klassen erscheinen, aber klar als 'class:' markiert
    assert "class:container_inventory" in prompt
    assert "class:workspace_read" in prompt

    # Keine rohen Tool-Namen aus der Live-Discovery duerfen im Self-Context-
    # Block landen. Ausnahme: das Wort 'tool' selbst ist erlaubt.
    self_context_start = prompt.find("## Verifizierter Self-Context")
    assert self_context_start >= 0
    next_section = prompt.find("\n## ", self_context_start + 1)
    self_context_block = prompt[self_context_start: next_section if next_section > 0 else len(prompt)]
    for tool_name in raw_live_tool_names:
        assert tool_name not in self_context_block, (
            f"Drift verletzt docs/34: roher Tool-Name '{tool_name}' im Self-Context-Block — "
            "Tool-Namen gehoeren nur in den 'VERFUEGBARE TOOLS'-Block (Live-Discovery)."
        )
