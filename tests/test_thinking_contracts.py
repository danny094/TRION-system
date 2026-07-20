"""Tests für core.thinking.contracts — P1 Regression (Doc 51).

Abgedeckt:
- PlanStep-Backward-Compat: Felder ohne done_when/required_evidence bleiben valide
- Neue Felder haben korrekte Defaults (done_when="", required_evidence=[])
- Neue Felder können gesetzt werden
- Dataclass-Gleichheit und Immutability (frozen=True)
"""
from core.thinking.contracts import PlanStep, RiskLevel


def test_planstep_without_new_fields_remains_valid():
    """Backward-Compat: PlanStep ohne done_when/required_evidence konstruierbar."""
    step = PlanStep(
        step_id="s1",
        title="Deploy",
        goal="Run container",
        tool="deploy_tool",
        tool_arguments={"env": "prod"},
    )
    assert step.step_id == "s1"
    assert step.tool == "deploy_tool"


def test_planstep_done_when_default_is_empty_string():
    step = PlanStep(step_id="s1", title="T", goal="G")
    assert step.done_when == ""


def test_planstep_required_evidence_default_is_empty_list():
    step = PlanStep(step_id="s1", title="T", goal="G")
    assert step.required_evidence == []


def test_planstep_required_evidence_default_is_independent_per_instance():
    """field(default_factory=list) — kein geteiltes Mutable-Default."""
    s1 = PlanStep(step_id="s1", title="T", goal="G")
    s2 = PlanStep(step_id="s2", title="T", goal="G")
    assert s1.required_evidence is not s2.required_evidence


def test_planstep_done_when_can_be_set():
    step = PlanStep(step_id="s1", title="T", goal="G", done_when="file_created")
    assert step.done_when == "file_created"


def test_planstep_required_evidence_can_be_set():
    step = PlanStep(
        step_id="s1", title="T", goal="G",
        required_evidence=["file_content", "tool_result"],
    )
    assert step.required_evidence == ["file_content", "tool_result"]


def test_planstep_all_fields_combined():
    step = PlanStep(
        step_id="s1",
        title="Verify",
        goal="Check output",
        tool="verify_tool",
        tool_arguments={"path": "/out"},
        timeout_s=60.0,
        risk=RiskLevel.SAFE,
        done_when="exit_code:0",
        required_evidence=["tool_result"],
    )
    assert step.done_when == "exit_code:0"
    assert step.required_evidence == ["tool_result"]
    assert step.timeout_s == 60.0


def test_planstep_is_frozen():
    step = PlanStep(step_id="s1", title="T", goal="G")
    try:
        step.done_when = "mutated"  # type: ignore[misc]
        raise AssertionError("should have raised FrozenInstanceError")
    except Exception as exc:
        assert "frozen" in str(type(exc).__name__).lower() or "cannot assign" in str(exc).lower()


def test_planstep_equality_includes_new_fields():
    s1 = PlanStep(step_id="s1", title="T", goal="G", done_when="file_created")
    s2 = PlanStep(step_id="s1", title="T", goal="G", done_when="file_created")
    s3 = PlanStep(step_id="s1", title="T", goal="G", done_when="exit_code:0")
    assert s1 == s2
    assert s1 != s3
