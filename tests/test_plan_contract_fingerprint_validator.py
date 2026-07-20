import asyncio
from types import SimpleNamespace

import pytest

from core.output.contracts import OutputResult
from core.pipeline import runner
from core.pipeline.plan_contract_validator import bind_validated_replanner
from core.thinking.contracts import PlanContractViolation, PlanStep, RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult
from tests._core_pipeline_request_helpers import core_pipeline_request
from tests.operation_contract_context import canonical_contract_context


def _plan(tool: str, *, needs_task_loop: bool = False) -> ThinkingPlan:
    return ThinkingPlan(
        intent="run_tools",
        steps=[PlanStep(step_id="s1", title="Step", goal="Run", tool=tool)],
        needs_task_loop=needs_task_loop,
        risk_level=RiskLevel.SAFE,
        plan_id="plan-fp",
    )


def _context(fingerprint: str | None) -> dict:
    context = {
        "selected_tool_details": _tool_truth(),
        "context": {},
    }
    if fingerprint is not None:
        frame = canonical_contract_context(
            domain="memory", primary_operation="search", allowed_operations=("search",),
            allowed_transitions=(), required_evidence=("memory_context",),
            scope_lock="assistant_identity",
        )["routing_frame"]
        if fingerprint not in {"fp-1", "same-fp"}:
            frame["operation_contract_fingerprint"] = fingerprint
        context["context"]["routing_frame"] = frame
    return context


def _tool_truth() -> list[dict]:
    return [{
        "name": "allowed_tool",
        "capability_domain": "memory",
        "capability_operation": "search",
        "capability_evidence_types": ["memory_context"],
        "capability_required_args": [],
        "capability_target_scopes": ["assistant_identity"],
        "capability_risk": "read_only",
    }]


def test_initial_plan_with_tool_missing_fingerprint_is_rejected_before_verifier(monkeypatch):
    seen = {"verifier": False}
    monkeypatch.setattr(
        runner,
        "build_thinking_stage",
        lambda *_a, **_k: SimpleNamespace(plan=_plan("allowed_tool"), thinking_context=_context(None)),
    )

    def verifier(*_args, **_kwargs):
        seen["verifier"] = True
        return VerifierResult(verdict=Verdict.APPROVED, reason="should_not_run")

    async def output(*_args, **_kwargs):
        return OutputResult(content="should not render")

    monkeypatch.setattr(runner, "verify_plan", verifier)
    response = asyncio.run(runner.run_chat(core_pipeline_request("Run tool"), output_fn=output))

    assert seen["verifier"] is False
    assert response.validation_passed is False
    assert response.content == "Die Anfrage konnte nicht freigegeben werden."


def test_initial_plan_with_tool_and_fingerprint_reaches_verifier(monkeypatch):
    seen = {"verifier": False}
    monkeypatch.setattr(
        runner,
        "build_thinking_stage",
        lambda *_a, **_k: SimpleNamespace(plan=_plan("allowed_tool"), thinking_context=_context("fp-1")),
    )

    def verifier(*_args, **_kwargs):
        seen["verifier"] = True
        return VerifierResult(verdict=Verdict.APPROVED, reason="ok")

    async def output(*_args, **_kwargs):
        return OutputResult(content="ok")

    monkeypatch.setattr(runner, "verify_plan", verifier)
    response = asyncio.run(runner.run_chat(core_pipeline_request("Run tool"), output_fn=output))

    assert seen["verifier"] is True
    assert response.content == "ok"


def test_replan_wrapper_blocks_missing_fingerprint_context():
    replanner = bind_validated_replanner(
        lambda *_a, **_k: _plan("allowed_tool", needs_task_loop=True),
        _tool_truth(),
    )

    with pytest.raises(PlanContractViolation, match="plan_contract_missing_fingerprint"):
        replanner()


def test_replan_wrapper_blocks_fingerprint_mismatch():
    replanner = bind_validated_replanner(
        lambda *_a, **_k: _plan("allowed_tool", needs_task_loop=True),
        _tool_truth(),
        context=_context("routing-fp"),
        stored_fingerprint="stored-fp",
    )

    with pytest.raises(PlanContractViolation, match="plan_contract_fingerprint_mismatch"):
        replanner()


def test_replan_wrapper_allows_matching_fingerprint():
    context = _context("same-fp")
    fingerprint = context["context"]["routing_frame"]["operation_contract_fingerprint"]
    replanner = bind_validated_replanner(
        lambda *_a, **_k: _plan("allowed_tool", needs_task_loop=True),
        _tool_truth(),
        context=context,
        stored_fingerprint=fingerprint,
    )

    assert replanner().plan_id == "plan-fp"
