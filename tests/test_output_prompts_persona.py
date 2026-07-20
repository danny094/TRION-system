from core.output.prompts import build_output_system_prompt
from core.output.persona_runtime import get_runtime_persona_prompt
from core.thinking.contracts import RiskLevel, ThinkingPlan
from tests._output_prompts_helpers import plan_answer_user


def test_output_prompt_uses_runtime_persona(monkeypatch):
    from core.output import prompts

    monkeypatch.setattr(
        prompts,
        "get_runtime_persona_prompt",
        lambda _context: "RUNTIME PERSONA",
    )
    prompt = build_output_system_prompt(plan_answer_user(), {})
    assert prompt.startswith("RUNTIME PERSONA")


def test_runtime_persona_does_not_inject_concrete_tool_names():
    # P11.0 SP4: Quelle ist available_tool_details (die gefilterte
    # ToolDescriptor-Projektion), nicht die wirkungslose available_tools-
    # Namensliste - siehe core/output/persona_runtime.py::_dynamic_context().
    context = {
        "orchestrator": {
            "available_tool_details": [
                {
                    "name": "get_system_info",
                    "mcp": "runtime-hardware",
                    "description": "Inspect hardware metrics.",
                },
                {
                    "name": "home_read",
                    "mcp": "container-commander",
                    "description": "Read files from TRION home.",
                },
                {
                    "name": "autonomy_cron_create_job",
                    "mcp": "cron",
                    "description": "Create a cron job.",
                },
            ],
        },
    }
    prompt = get_runtime_persona_prompt(context)
    assert "get_system_info" not in prompt
    assert "home_read" not in prompt
    assert "autonomy_cron_create_job" not in prompt
    assert "container-commander" not in prompt
    assert "trion-home" in prompt.lower()


def test_output_prompt_adds_dialogue_rule_for_smalltalk_without_anthropomorphic_claims():
    plan = ThinkingPlan(
        intent="answer_user",
        steps=[],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
        reasoning="test",
        context_hints={"dialogue_act": "smalltalk", "user_text": "Wie ist es fuer dich?"},
    )

    prompt = build_output_system_prompt(plan, {})

    assert "## Dialogregel" in prompt
    assert "keine menschlichen Gefuehle, Erinnerungen, Identitaets- oder Koerperbehauptungen erfinden" in prompt
