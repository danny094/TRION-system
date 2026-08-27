import ast
from pathlib import Path

import pytest

from core.output.renderable_evidence import build_renderable_evidence
from core.pipeline.output_evidence_contracts import (
    OutputEvidenceHandoff,
    OutputEvidenceItem,
    OutputEvidenceState,
)
from core.pipeline.output_stage import build_output_stage
from core.thinking.contracts import RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult


ROOT = Path(__file__).resolve().parents[1]
RENDERER_PATH = ROOT / "core" / "output" / "renderable_evidence.py"
LEGACY_RENDERER_PATHS = (
    ROOT / "core" / "output" / "direct_tool_output.py",
    ROOT / "core" / "output" / "tool_grounding.py",
    ROOT / "core" / "output" / "truth_renderer.py",
)
SELECTION_PATH = ROOT / "core" / "output" / "grounded_output_selection.py"
RESPONSE_INTENTS_PATH = ROOT / "utils" / "response_intents.py"


def _handoff() -> OutputEvidenceHandoff:
    return OutputEvidenceHandoff(
        OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE,
        (OutputEvidenceItem({"value": "verified"}),),
    )


def _plan() -> ThinkingPlan:
    return ThinkingPlan("answer", [], False, RiskLevel.SAFE)


def test_renderer_accepts_only_typed_handoff() -> None:
    evidence = build_renderable_evidence(_handoff())

    assert len(evidence) == 1
    with pytest.raises(TypeError):
        build_renderable_evidence([{"value": "untyped"}])


def test_output_stage_carries_renderer_result_outside_context() -> None:
    handoff = _handoff()
    stage = build_output_stage(
        user_text="status",
        thinking_plan=_plan(),
        verifier_result=VerifierResult(verdict=Verdict.APPROVED, reason="ok"),
        orchestrator_context={},
        document_tools_context={},
        output_evidence=handoff,
        document_context=None,
        stream=False,
    )

    assert stage.output_request.renderable_evidence == build_renderable_evidence(handoff)
    assert "renderable_evidence" not in stage.output_request.context


def test_renderer_has_no_untyped_reconstruction_source() -> None:
    source = RENDERER_PATH.read_text(encoding="utf-8")

    for forbidden in ("tool_name", "thinking_plan", "artifacts", "evidence_type"):
        assert forbidden not in source


def test_legacy_renderer_modules_are_removed() -> None:
    assert all(not path.exists() for path in LEGACY_RENDERER_PATHS)


def test_grounded_output_selection_keeps_only_shared_normalizer() -> None:
    tree = ast.parse(SELECTION_PATH.read_text(encoding="utf-8"))
    definitions = {
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert definitions == {"_normalize_text"}


def test_removed_capability_message_leaves_no_path_parser() -> None:
    tree = ast.parse(RESPONSE_INTENTS_PATH.read_text(encoding="utf-8"))
    definitions = {
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "_requested_path" not in definitions
