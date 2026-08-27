import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMPTS_PATH = ROOT / "core" / "output" / "prompts.py"
PUBLIC_CONTRACT_PROMPT_PATH = ROOT / "core" / "output" / "public_contract_prompt.py"


def _definitions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_prompt_split_has_one_owner_per_responsibility() -> None:
    assert PROMPTS_PATH.read_text(encoding="utf-8").count("\n") + 1 <= 200
    assert PUBLIC_CONTRACT_PROMPT_PATH.read_text(encoding="utf-8").count("\n") + 1 <= 200
    assert _definitions(PUBLIC_CONTRACT_PROMPT_PATH) == {
        "build_contract_blocks",
        "build_verified_evidence_block",
    }


def test_prompt_facade_drops_legacy_raw_projection_owners() -> None:
    definitions = _definitions(PROMPTS_PATH)

    assert {
        "_contract_blocks",
        "_memory_block",
        "_missing_memory_answer_risk",
        "_task_loop_block",
        "_grounded_tool_block",
        "_home_context_block",
        "_self_context_block",
    }.isdisjoint(definitions)


def test_messages_pass_typed_evidence_without_context_projection() -> None:
    prompts_source = PROMPTS_PATH.read_text(encoding="utf-8")
    messages_source = (ROOT / "core" / "output" / "messages.py").read_text(encoding="utf-8")

    assert "from core.output.public_contract_prompt import" in prompts_source
    assert "renderable_evidence=output_request.renderable_evidence" in messages_source
    assert 'context["renderable_evidence"]' not in prompts_source
