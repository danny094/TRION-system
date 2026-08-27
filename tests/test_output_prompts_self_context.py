from core.output.prompts import build_output_system_prompt
from tests._output_prompts_helpers import plan_answer_user


def test_raw_home_context_is_not_projected() -> None:
    context = {
        "orchestrator": {
            "context": {
                "home_context": {
                    "verified": True,
                    "home_root": "RAW_HOME_SENTINEL",
                    "available_capability_classes": ["RAW_CAPABILITY_SENTINEL"],
                }
            }
        }
    }

    prompt = build_output_system_prompt(plan_answer_user(), context)

    assert "RAW_HOME_SENTINEL" not in prompt
    assert "RAW_CAPABILITY_SENTINEL" not in prompt
    assert "## Verifizierter Home-/Scope-Kontext" not in prompt


def test_raw_self_context_is_not_projected() -> None:
    context = {
        "orchestrator": {
            "context": {
                "self_context": {
                    "identity": {"name": "RAW_SELF_SENTINEL"},
                    "capabilities": [{"name": "RAW_TOOL_SENTINEL"}],
                }
            }
        }
    }

    prompt = build_output_system_prompt(plan_answer_user(), context)

    assert "RAW_SELF_SENTINEL" not in prompt
    assert "RAW_TOOL_SENTINEL" not in prompt
    assert "## Verifizierter Self-Context" not in prompt
