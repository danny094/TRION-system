"""Tests für core.task_loop.outcome_evaluator.

Abgedeckte Pfade (Doc 51, Phase 3 — Abnahmekriterien E3):
- Backward-Compat: PlanStep ohne Kriterien → COMPLETE
- required_evidence fehlt, Budget vorhanden → REPLAN
- required_evidence vorhanden → COMPLETE
- CAPABILITY_GAP: geforderter Typ nicht in available_evidence_types → BLOCK
- Budget erschöpft + Objective nicht erfüllt → BLOCK
"""
from core.task_loop.contracts import EvidenceArtifact, StopReason
from core.task_loop.outcome_evaluator import OutcomeAction, OutcomeDecision, evaluate
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _plan(*steps: PlanStep) -> ThinkingPlan:
    return ThinkingPlan(
        intent="run_tools",
        steps=list(steps),
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        context_hints={"user_text": "test"},
        plan_id="plan-1",
    )


def _step(
    step_id: str,
    *,
    done_when: str = "",
    required_evidence: list | None = None,
) -> PlanStep:
    return PlanStep(
        step_id=step_id,
        title=f"Step {step_id}",
        goal=f"Goal {step_id}",
        tool="demo_tool",
        tool_arguments={},
        done_when=done_when,
        required_evidence=required_evidence or [],
    )


def _artifact(step_id: str, artifact_type: str, content: str = "", **metadata) -> EvidenceArtifact:
    return EvidenceArtifact(step_id=step_id, artifact_type=artifact_type, content=content, metadata=metadata)


# ---------------------------------------------------------------------------
# 1. Backward-Compat: kein Kriterium → COMPLETE
# ---------------------------------------------------------------------------

def test_backward_compat_no_criteria_returns_complete():
    plan = _plan(_step("s1"))
    result = evaluate(plan, [])
    assert result.action == OutcomeAction.COMPLETE


def test_backward_compat_multiple_steps_no_criteria_returns_complete():
    plan = _plan(_step("s1"), _step("s2"), _step("s3"))
    result = evaluate(plan, [])
    assert result.action == OutcomeAction.COMPLETE


# ---------------------------------------------------------------------------
# 2. required_evidence fehlt → REPLAN (Budget vorhanden)
# ---------------------------------------------------------------------------

def test_required_evidence_missing_triggers_replan():
    plan = _plan(_step("s1", required_evidence=["file_content"]))
    result = evaluate(plan, [], replan_budget_remaining=True)
    assert result.action == OutcomeAction.REPLAN
    assert result.stop_reason == StopReason.OBJECTIVE_NOT_MET


def test_required_evidence_wrong_type_triggers_replan():
    plan = _plan(_step("s1", required_evidence=["file_content"]))
    artifacts = [_artifact("s1", "tool_result")]
    result = evaluate(plan, artifacts, replan_budget_remaining=True)
    assert result.action == OutcomeAction.REPLAN


# ---------------------------------------------------------------------------
# 3. required_evidence vorhanden → COMPLETE
# ---------------------------------------------------------------------------

def test_required_evidence_present_returns_complete():
    plan = _plan(_step("s1", required_evidence=["file_content"]))
    artifacts = [_artifact("s1", "file_content", validated_evidence=True, operation_contract_fingerprint="fp")]
    result = evaluate(plan, artifacts, expected_operation_contract_fingerprint="fp")
    assert result.action == OutcomeAction.COMPLETE


def test_required_evidence_multiple_types_all_present_returns_complete():
    plan = _plan(_step("s1", required_evidence=["file_content", "semantic_search_result"]))
    artifacts = [
        _artifact("s1", "file_content", validated_evidence=True, operation_contract_fingerprint="fp"),
        _artifact("s1", "semantic_search_result", validated_evidence=True, operation_contract_fingerprint="fp"),
    ]
    result = evaluate(plan, artifacts, expected_operation_contract_fingerprint="fp")
    assert result.action == OutcomeAction.COMPLETE


def test_required_evidence_artifact_from_other_step_not_counted():
    """Artifacts eines anderen Steps dürfen nicht für s1 zählen."""
    plan = _plan(_step("s1", required_evidence=["file_content"]))
    artifacts = [_artifact("s2", "file_content")]  # anderer step_id
    result = evaluate(plan, artifacts, replan_budget_remaining=True)
    assert result.action == OutcomeAction.REPLAN


# ---------------------------------------------------------------------------
# 4. CAPABILITY_GAP: geforderter Typ nicht in available_evidence_types → BLOCK
# ---------------------------------------------------------------------------

def test_capability_gap_triggers_block():
    plan = _plan(_step("s1", required_evidence=["thermal_scan"]))
    result = evaluate(
        plan,
        [],
        available_evidence_types=frozenset({"tool_result", "semantic_search_result"}),
        replan_budget_remaining=True,
    )
    assert result.action == OutcomeAction.BLOCK
    assert result.stop_reason == StopReason.CAPABILITY_GAP


def test_capability_gap_not_triggered_when_type_available():
    plan = _plan(_step("s1", required_evidence=["thermal_scan"]))
    result = evaluate(
        plan,
        [],
        available_evidence_types=frozenset({"thermal_scan"}),
        replan_budget_remaining=True,
    )
    # Typ ist grundsätzlich verfügbar → REPLAN (noch nicht gesammelt)
    assert result.action == OutcomeAction.REPLAN


def test_empty_available_evidence_types_does_not_trigger_capability_gap():
    """Kein available_evidence_types gesetzt → Capability-Gap-Prüfung übersprungen."""
    plan = _plan(_step("s1", required_evidence=["thermal_scan"]))
    result = evaluate(plan, [], available_evidence_types=frozenset(), replan_budget_remaining=True)
    assert result.action == OutcomeAction.REPLAN


# ---------------------------------------------------------------------------
# 5. Budget erschöpft + Objective nicht erfüllt → BLOCK
# ---------------------------------------------------------------------------

def test_budget_exhausted_returns_block():
    plan = _plan(_step("s1", required_evidence=["file_content"]))
    result = evaluate(plan, [], replan_budget_remaining=False)
    assert result.action == OutcomeAction.BLOCK
    assert result.stop_reason == StopReason.OBJECTIVE_NOT_MET


# ---------------------------------------------------------------------------
# 6. Mehrere Steps — erster Fehler stoppt Auswertung
# ---------------------------------------------------------------------------

def test_first_failing_step_stops_evaluation():
    plan = _plan(
        _step("s1", required_evidence=["file_content"]),
        _step("s2", required_evidence=["tool_result"]),
    )
    # s1 fehlt → s2 wird gar nicht geprüft
    artifacts = [_artifact("s2", "tool_result")]
    result = evaluate(plan, artifacts, replan_budget_remaining=True)
    assert result.action == OutcomeAction.REPLAN


# ---------------------------------------------------------------------------
# 7. P7: Fantasy-Typ beweist kein Whitelist-Check (T11)
# ---------------------------------------------------------------------------

def test_capability_gap_with_fantasy_evidence_type_triggers_block():
    """T11: 'quantum_probe' im required_evidence + leere available_evidence_types → BLOCK.

    Beweist, dass kein Whitelist-Check für evidence_type-Namen in Core existiert.
    quantum_probe ist ein unbekannter Typ — kein Produktivcode kennt ihn.
    """
    plan = _plan(_step("s1", required_evidence=["quantum_probe"]))
    # available_evidence_types muss non-empty sein damit CAPABILITY_GAP ausgelöst wird —
    # leere frozenset bedeutet "keine Capability-Info registriert" → sicherer Fallback: REPLAN.
    # "other_type" ist ein bekannter Typ, "quantum_probe" fehlt → BLOCK.
    result = evaluate(plan, [], available_evidence_types=frozenset({"other_type"}))
    assert result.action == OutcomeAction.BLOCK
    assert result.stop_reason == StopReason.CAPABILITY_GAP
