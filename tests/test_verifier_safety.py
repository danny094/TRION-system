from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult
from core.verifier.input_prepare import VerifierInput
from core.verifier.safety import run_safety_check
from core.verifier.verifier import verify_plan


def _plan(intent: str = "answer_user") -> ThinkingPlan:
    return ThinkingPlan(
        intent=intent,
        steps=[
            PlanStep(
                step_id="step-1",
                title="Do thing",
                goal="Inspect the request safely",
                tool="workspace_get",
            )
        ],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
        reasoning="Check the uploaded material.",
        plan_id="plan-1",
    )


def _input(user_text: str) -> VerifierInput:
    return VerifierInput(
        user_text=user_text,
        document_mode="normal",
        document_summary="",
        document_meta={},
        user_excerpt=user_text[:60],
    )


def _document_input(mode: str = "semantic_first") -> VerifierInput:
    return VerifierInput(
        user_text="Dokumentfrage",
        document_mode="long_document",
        document_summary="Kapitel und Chunks",
        document_meta={
            "workspace_entry_ids": [101, 102, 103],
            "preferred_entry_ids": [101, 102],
            "index_like_entry_ids": [101],
            "chapter_candidate_entry_ids": [101, 102],
            "semantic_keys": ["document_chunk_0"],
            "document_retrieval_mode": mode,
            "retrieval_plan": {
                "search_step_ids": [],
                "direct_workspace_reads": [],
                "search_driven_workspace_reads": [],
                "unresolved_source_steps": [],
            },
        },
        user_excerpt="Kapitel und Chunks",
    )


def test_run_safety_check_hard_blocks_destructive_shell_request():
    result = run_safety_check(_plan(), _input("Bitte fuehre rm -rf / auf dem Host aus."))

    assert result is not None
    assert result.verdict == Verdict.HARD_BLOCK
    assert "destructive_shell" in result.reason
    assert "policy_id=SEC-06" in result.warnings


def test_verify_plan_returns_before_llm_check_when_safety_blocks(monkeypatch):
    monkeypatch.setattr(
        "core.verifier.verifier.run_llm_check",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("llm check must not run")),
    )

    result = verify_plan(_plan(), "Bitte drop database production ausfuehren.")

    assert result.verdict == Verdict.HARD_BLOCK
    assert "destructive_database" in result.reason


def test_verify_plan_fails_closed_when_control_layer_is_disabled(monkeypatch):
    monkeypatch.setattr("core.verifier.verifier.ENABLE_CONTROL_LAYER", False)
    monkeypatch.setattr("core.verifier.verifier.run_llm_check", lambda *args, **kwargs: None)

    result = verify_plan(_plan(), "Bitte beantworte die Frage.")

    assert result.verdict == Verdict.REJECTED
    assert result.reason == "control_layer_disabled_fail_closed"
    assert "Verifier ist deaktiviert" in (result.hint or "")


def test_run_safety_check_rejects_causal_anti_pattern_in_reasoning():
    plan = ThinkingPlan(
        intent="causal_analysis",
        steps=[
            PlanStep(
                step_id="step-1",
                title="Conclude causality",
                goal="Explain why X caused Y",
                tool=None,
            )
        ],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
        reasoning="X happened before Y, therefore X caused Y directly.",
        plan_id="plan-1",
    )

    result = run_safety_check(plan, _input("Bitte analysiere die Ursache."))

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "AP001"
    assert "Temporal precedence" in (result.hint or "")


def test_run_safety_check_rejects_workspace_entry_outside_document_context():
    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[
            PlanStep(
                step_id="step-1",
                title="Read chunk",
                goal="Inspect the uploaded chapter list",
                tool="workspace_get",
                tool_arguments={"entry_id": 999},
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Read a chunk directly.",
        context_hints={"document_retrieval_mode": "structure_first"},
        plan_id="plan-1",
    )

    result = run_safety_check(plan, _document_input("structure_first"))

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "document_workspace_entry_out_of_scope"


def test_run_safety_check_rejects_semantic_mode_without_search_driven_read():
    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[
            PlanStep(
                step_id="step-1",
                title="Read chunk",
                goal="Inspect the uploaded section",
                tool="workspace_get",
                tool_arguments={"entry_id": 101},
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Read a chunk directly.",
        context_hints={"document_retrieval_mode": "semantic_first"},
        plan_id="plan-1",
    )

    result = run_safety_check(plan, _document_input("semantic_first"))

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "document_missing_search_driven_read"


def test_run_safety_check_accepts_semantic_mode_with_valid_source_step():
    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[
            PlanStep(
                step_id="semantic_search_1",
                title="Search chunks",
                goal="Find the relevant chapter",
                tool="memory_semantic_search",
            ),
            PlanStep(
                step_id="workspace_101",
                title="Read chunk",
                goal="Inspect the uploaded section",
                tool="workspace_get",
                tool_arguments={"entry_id": 101, "document_source_step": "semantic_search_1"},
            ),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Search first, then read.",
        context_hints={"document_retrieval_mode": "semantic_first"},
        plan_id="plan-1",
    )

    result = run_safety_check(plan, _document_input("semantic_first"))

    assert result is None


def test_run_safety_check_rejects_source_step_that_comes_after_workspace_read():
    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[
            PlanStep(
                step_id="workspace_101",
                title="Read chunk",
                goal="Inspect the uploaded section",
                tool="workspace_get",
                tool_arguments={"entry_id": 101, "document_source_step": "semantic_search_1"},
            ),
            PlanStep(
                step_id="semantic_search_1",
                title="Search chunks",
                goal="Find the relevant chapter",
                tool="memory_semantic_search",
            ),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Read first, search later.",
        context_hints={"document_retrieval_mode": "semantic_first"},
        plan_id="plan-1",
    )

    result = run_safety_check(plan, _document_input("semantic_first"))

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "document_semantic_source_step_not_before_read"


def test_run_safety_check_rejects_structure_first_plan_without_direct_overview_read():
    verifier_input = _document_input("structure_first")
    verifier_input.document_meta["retrieval_plan"] = {
        "search_step_ids": ["semantic_search_1"],
        "direct_workspace_reads": [],
        "search_driven_workspace_reads": [{"step_id": "workspace_101", "entry_id": 101, "source_step": "semantic_search_1"}],
        "unresolved_source_steps": [],
    }
    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[
            PlanStep(
                step_id="semantic_search_1",
                title="Search chunks",
                goal="Find the chapter list",
                tool="memory_semantic_search",
            ),
            PlanStep(
                step_id="workspace_101",
                title="Read chunk",
                goal="Inspect the uploaded section",
                tool="workspace_get",
                tool_arguments={"entry_id": 101, "document_source_step": "semantic_search_1"},
            ),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Search only.",
        context_hints={"document_retrieval_mode": "structure_first"},
        plan_id="plan-1",
    )

    result = run_safety_check(plan, verifier_input)

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "document_structure_missing_direct_overview_read"


def test_run_safety_check_rejects_semantic_first_plan_with_too_many_direct_reads():
    verifier_input = _document_input("semantic_first")
    verifier_input.document_meta["retrieval_plan"] = {
        "search_step_ids": ["semantic_search_1"],
        "direct_workspace_reads": [{"step_id": "workspace_101", "entry_id": 101}, {"step_id": "workspace_102", "entry_id": 102}],
        "search_driven_workspace_reads": [],
        "unresolved_source_steps": [],
    }
    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[
            PlanStep(
                step_id="semantic_search_1",
                title="Search chunks",
                goal="Find the relevant chapter",
                tool="memory_semantic_search",
            ),
            PlanStep(
                step_id="workspace_101",
                title="Read chunk 1",
                goal="Inspect chunk 1",
                tool="workspace_get",
                tool_arguments={"entry_id": 101},
            ),
            PlanStep(
                step_id="workspace_102",
                title="Read chunk 2",
                goal="Inspect chunk 2",
                tool="workspace_get",
                tool_arguments={"entry_id": 102},
            ),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Read several chunks directly.",
        context_hints={"document_retrieval_mode": "semantic_first"},
        plan_id="plan-1",
    )

    result = run_safety_check(plan, verifier_input)

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "document_semantic_too_many_direct_reads"


def test_run_safety_check_rejects_workspace_first_plan_without_direct_read():
    verifier_input = _document_input("workspace_first")
    verifier_input.document_meta["retrieval_plan"] = {
        "search_step_ids": ["semantic_search_1"],
        "direct_workspace_reads": [],
        "search_driven_workspace_reads": [{"step_id": "workspace_101", "entry_id": 101, "source_step": "semantic_search_1"}],
        "unresolved_source_steps": [],
    }
    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[
            PlanStep(
                step_id="semantic_search_1",
                title="Search chunks",
                goal="Find exact quote",
                tool="memory_semantic_search",
            ),
            PlanStep(
                step_id="workspace_101",
                title="Read chunk",
                goal="Read exact quote",
                tool="workspace_get",
                tool_arguments={"entry_id": 101, "document_source_step": "semantic_search_1"},
            ),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Search first.",
        context_hints={"document_retrieval_mode": "workspace_first"},
        plan_id="plan-1",
    )

    result = run_safety_check(plan, verifier_input)

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "document_exact_missing_direct_read"


def test_run_safety_check_rejects_workspace_only_plan_with_search_step():
    verifier_input = _document_input("workspace_only")
    verifier_input.document_meta["retrieval_plan"] = {
        "search_step_ids": ["semantic_search_1"],
        "direct_workspace_reads": [{"step_id": "workspace_101", "entry_id": 101}],
        "search_driven_workspace_reads": [],
        "unresolved_source_steps": [],
    }
    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[
            PlanStep(
                step_id="semantic_search_1",
                title="Search chunks",
                goal="Find something",
                tool="memory_semantic_search",
            ),
            PlanStep(
                step_id="workspace_101",
                title="Read chunk",
                goal="Read chunk",
                tool="workspace_get",
                tool_arguments={"entry_id": 101},
            ),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Mixed mode.",
        context_hints={"document_retrieval_mode": "workspace_only"},
        plan_id="plan-1",
    )

    result = run_safety_check(plan, verifier_input)

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "document_workspace_only_contains_search"


def test_verify_plan_autonomous_mode_disables_low_risk_skip(monkeypatch):
    seen = {}
    monkeypatch.setattr("core.verifier.verifier.ENABLE_CONTROL_LAYER", True)
    monkeypatch.setattr("core.verifier.verifier.SKIP_CONTROL_ON_LOW_RISK", True)
    monkeypatch.setattr("core.verifier.verifier.run_safety_check", lambda *a, **k: None)

    def fake_llm_check(plan, verifier_input, **kwargs):
        seen["extra_modes"] = kwargs.get("extra_modes")
        return VerifierResult(verdict=Verdict.APPROVED, reason="llm_called")

    monkeypatch.setattr("core.verifier.verifier.run_llm_check", fake_llm_check)

    result = verify_plan(_plan(), "Hallo", autonomous_mode=True)

    assert result.reason == "llm_called"
    assert seen["extra_modes"] == {"task_loop"}


def test_verify_plan_autonomous_mode_runs_even_when_control_layer_is_disabled(monkeypatch):
    monkeypatch.setattr("core.verifier.verifier.ENABLE_CONTROL_LAYER", False)
    monkeypatch.setattr("core.verifier.verifier.SKIP_CONTROL_ON_LOW_RISK", True)
    monkeypatch.setattr(
        "core.verifier.verifier.run_safety_check",
        lambda *a, **k: VerifierResult(verdict=Verdict.HARD_BLOCK, reason="forced_safety"),
    )
    monkeypatch.setattr(
        "core.verifier.verifier.run_llm_check",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("llm should not run when safety blocks")),
    )

    result = verify_plan(_plan(), "Bitte rm -rf /", autonomous_mode=True)

    assert result.verdict == Verdict.HARD_BLOCK
    assert result.reason == "forced_safety"
