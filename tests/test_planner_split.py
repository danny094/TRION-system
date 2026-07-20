"""Guardrail-Tests für den planner.py → planner/-Package-Split.

Prüft:
1. Importpfad unverändert: `from core.thinking.planner import build_plan_from_analysis`
2. Verhalten von build_plan_from_analysis bleibt nach dem Split identisch.
3. Alle Submodule existieren und exportieren die erwarteten Namen.
"""
from __future__ import annotations

from typing import Any, Dict

import pytest

from core.thinking.planner import build_plan_from_analysis
from core.thinking.contracts import ThinkingPlan, PlanStep, RiskLevel


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _raw(
    intent: str = "answer_user",
    tools: list[str] | None = None,
    *,
    hallucination_risk: str = "low",
    needs_loop: bool = False,
    repeat_count_hint: int = 1,
    response_tone: str = "neutral",
    response_length_hint: str = "medium",
    task_loop_kind: str = "",
    reasoning_type: str = "direct",
    needs_visible_progress: bool = False,
) -> Dict[str, Any]:
    plan: Dict[str, Any] = {"intent": intent, "hallucination_risk": hallucination_risk}
    if tools is not None:
        plan["suggested_tools"] = tools
    plan["needs_loop"] = needs_loop
    plan["repeat_count_hint"] = repeat_count_hint
    plan["response_tone"] = response_tone
    plan["response_length_hint"] = response_length_hint
    plan["task_loop_kind"] = task_loop_kind
    plan["reasoning_type"] = reasoning_type
    plan["needs_visible_progress"] = needs_visible_progress
    return plan


def _orchestrator(
    selected_tools: list[str] | None = None,
    routing_frame: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {}
    if selected_tools is not None:
        ctx["selected_tools"] = selected_tools
    if routing_frame is not None:
        ctx["routing_frame"] = routing_frame
    return ctx


# ---------------------------------------------------------------------------
# Importpfad-Check (nach Split muss dieser Pfad weiterhin funktionieren)
# ---------------------------------------------------------------------------


class TestImportPath:
    def test_build_plan_from_analysis_importable(self):
        """Importpfad core.thinking.planner.build_plan_from_analysis bleibt nach Split stabil."""
        assert callable(build_plan_from_analysis)

    def test_submodule_frame_reader_importable(self):
        from core.thinking.planner.frame_reader import (
            routing_frame,
            needs_loop,
            repeat_count,
            selected_tool_detail,
        )
        assert callable(routing_frame)
        assert callable(needs_loop)
        assert callable(repeat_count)
        assert callable(selected_tool_detail)

    def test_submodule_plan_meta_importable(self):
        from core.thinking.planner.plan_meta import (
            risk_level,
            plan_id,
            response_projection,
            response_derivation,
            additional_evidence_need,
        )
        assert callable(risk_level)
        assert callable(plan_id)

    def test_submodule_tool_resolver_importable(self):
        from core.thinking.planner.tool_resolver import (
            tool_list,
            tool_detail_names,
            resolved_suggested_tools,
            should_backfill_selected_tools,
        )
        assert callable(resolved_suggested_tools)

    def test_submodule_step_builder_importable(self):
        from core.thinking.planner.step_builder import (
            build_steps,
            tool_steps,
        )
        assert callable(build_steps)
        assert callable(tool_steps)


# ---------------------------------------------------------------------------
# Verhalten: build_plan_from_analysis
# ---------------------------------------------------------------------------


class TestBuildPlanFromAnalysis:
    def test_no_tools_returns_answer_user_step(self):
        plan = build_plan_from_analysis(_raw(intent="answer_user"), user_text="Hi")
        assert isinstance(plan, ThinkingPlan)
        assert plan.intent == "answer_user"
        assert len(plan.steps) == 1
        assert plan.steps[0].tool is None

    def test_single_tool_returns_tool_step(self):
        plan = build_plan_from_analysis(
            _raw(intent="speichere das", tools=["memory_save"]),
            user_text="Speichere das",
        )
        assert plan.steps[0].tool == "memory_save"
        assert plan.suggested_tools == ["memory_save"]

    def test_high_hallucination_risk_sets_needs_confirmation(self):
        plan = build_plan_from_analysis(
            _raw(hallucination_risk="high"), user_text="Etwas riskantes"
        )
        assert plan.risk_level == RiskLevel.NEEDS_CONFIRMATION

    def test_low_hallucination_risk_sets_safe(self):
        plan = build_plan_from_analysis(_raw(hallucination_risk="low"), user_text="x")
        assert plan.risk_level == RiskLevel.SAFE

    def test_response_tone_passed_through(self):
        plan = build_plan_from_analysis(
            _raw(response_tone="mirror_user"), user_text="x"
        )
        assert plan.context_hints["response_tone"] == "mirror_user"

    def test_plan_id_contains_slug(self):
        plan = build_plan_from_analysis(
            _raw(intent="deploy container", tools=["request_container"]),
            user_text="Deploy",
        )
        assert "deploy" in plan.plan_id

    def test_loop_step_count_from_repeat_count_hint(self):
        plan = build_plan_from_analysis(
            _raw(
                intent="sync",
                tools=["memory_save"],
                needs_loop=True,
                repeat_count_hint=3,
            ),
            user_text="Sync dreimal",
        )
        assert len(plan.steps) == 3
        assert all(s.tool == "memory_save" for s in plan.steps)

    def test_backfill_from_orchestrator_selected_tools(self):
        """Wenn raw_plan keine tools hat, aber orchestrator_context.selected_tools, backfill."""
        ctx = _orchestrator(selected_tools=["memory_save"])
        plan = build_plan_from_analysis(
            _raw(
                intent="sync",
                tools=None,
                needs_loop=True,
                repeat_count_hint=2,
            ),
            user_text="Sync zweimal",
            orchestrator_context=ctx,
        )
        assert plan.suggested_tools == ["memory_save"]

    def test_routing_frame_execution_mode_in_context_hints(self):
        ctx = _orchestrator(routing_frame={"execution_mode": "single_tool"})
        plan = build_plan_from_analysis(_raw(), user_text="x", orchestrator_context=ctx)
        assert plan.context_hints["routing_execution_mode"] == "single_tool"

    def test_needs_loop_from_routing_frame(self):
        ctx = _orchestrator(
            selected_tools=["memory_save"],
            routing_frame={
                "execution_mode": "loop",
                "source_signals": {"repeat_count": 2},
            },
        )
        plan = build_plan_from_analysis(
            _raw(intent="loop", tools=["memory_save"]),
            user_text="loop",
            orchestrator_context=ctx,
        )
        assert plan.context_hints["needs_loop"] is True


# ---------------------------------------------------------------------------
# Verhalten: frame_reader Hilfsfunktionen (direkt)
# ---------------------------------------------------------------------------


class TestFrameReader:
    def test_routing_frame_reads_direct_key(self):
        from core.thinking.planner.frame_reader import routing_frame
        ctx = {"routing_frame": {"intent_kind": "action_request"}}
        assert routing_frame(ctx) == {"intent_kind": "action_request"}

    def test_routing_frame_empty_when_absent(self):
        from core.thinking.planner.frame_reader import routing_frame
        assert routing_frame(None) == {}
        assert routing_frame({}) == {}

    def test_needs_loop_true_from_raw_plan(self):
        from core.thinking.planner.frame_reader import needs_loop
        assert needs_loop({"needs_loop": True}, None) is True

    def test_needs_loop_true_from_execution_mode(self):
        from core.thinking.planner.frame_reader import needs_loop
        ctx = {"routing_frame": {"execution_mode": "loop"}}
        assert needs_loop({}, ctx) is True

    def test_needs_loop_false_when_neither(self):
        from core.thinking.planner.frame_reader import needs_loop
        assert needs_loop({}, None) is False

    def test_repeat_count_from_raw_plan(self):
        from core.thinking.planner.frame_reader import repeat_count
        assert repeat_count({"repeat_count_hint": 3}, {}) == 3

    def test_repeat_count_from_routing_frame_signals(self):
        from core.thinking.planner.frame_reader import repeat_count
        frame = {"source_signals": {"repeat_count": 4}}
        assert repeat_count({}, frame) == 4

    def test_repeat_count_minimum_one(self):
        from core.thinking.planner.frame_reader import repeat_count
        assert repeat_count({}, {}) == 1


# ---------------------------------------------------------------------------
# Verhalten: plan_meta Hilfsfunktionen (direkt)
# ---------------------------------------------------------------------------


class TestPlanMeta:
    def test_risk_level_high(self):
        from core.thinking.planner.plan_meta import risk_level
        assert risk_level({"hallucination_risk": "high"}) == RiskLevel.NEEDS_CONFIRMATION

    def test_risk_level_safe(self):
        from core.thinking.planner.plan_meta import risk_level
        assert risk_level({}) == RiskLevel.SAFE

    def test_plan_id_no_tools(self):
        from core.thinking.planner.plan_meta import plan_id
        pid = plan_id({"intent": "answer user"}, [])
        assert pid == "answer-user"

    def test_plan_id_with_tools(self):
        from core.thinking.planner.plan_meta import plan_id
        pid = plan_id({"intent": "deploy"}, ["request_container"])
        assert pid == "deploy-1-tools"

    def test_response_projection_none_when_absent(self):
        from core.thinking.planner.plan_meta import response_projection
        assert response_projection({}) is None

    def test_response_derivation_none_when_absent(self):
        from core.thinking.planner.plan_meta import response_derivation
        assert response_derivation({}) is None

    def test_additional_evidence_need_none_when_absent(self):
        from core.thinking.planner.plan_meta import additional_evidence_need
        assert additional_evidence_need({}) is None


# ---------------------------------------------------------------------------
# Verhalten: tool_resolver Hilfsfunktionen (direkt)
# ---------------------------------------------------------------------------


class TestToolResolver:
    def test_tool_list_from_strings(self):
        from core.thinking.planner.tool_resolver import tool_list
        assert tool_list(["a", "b", "a"]) == ["a", "b"]

    def test_tool_list_empty_on_non_iterable(self):
        from core.thinking.planner.tool_resolver import tool_list
        assert tool_list(None) == []
        assert tool_list("string") == []

    def test_tool_detail_names_from_dicts(self):
        from core.thinking.planner.tool_resolver import tool_detail_names
        raw = [{"name": "memory_save"}, {"name": "memory_search"}]
        assert tool_detail_names(raw) == ["memory_save", "memory_search"]

    def test_resolved_returns_raw_plan_tools_first(self):
        from core.thinking.planner.tool_resolver import resolved_suggested_tools
        result = resolved_suggested_tools(
            {"suggested_tools": ["memory_save"]}, None
        )
        assert result == ["memory_save"]

    def test_resolved_empty_when_no_tools_no_backfill(self):
        from core.thinking.planner.tool_resolver import resolved_suggested_tools
        assert resolved_suggested_tools({}, None) == []


# ---------------------------------------------------------------------------
# P7: _step_criteria — Completion-Criteria-Extraktion (T3–T5)
# ---------------------------------------------------------------------------


class TestStepCriteria:
    """T3–T5: _step_criteria liest done_when/required_evidence generisch aus raw_plan['steps']."""

    def test_returns_empty_dict_when_no_steps_key(self):
        """T3: raw_plan ohne 'steps' → leeres Dict — Backward-compat."""
        from core.thinking.planner.step_builder import _step_criteria
        assert _step_criteria({}) == {}
        assert _step_criteria({"intent": "x", "suggested_tools": ["tool_a"]}) == {}

    def test_extracts_done_when_and_required_evidence(self):
        """T4: raw_plan mit steps → dict korrekt befüllt."""
        from core.thinking.planner.step_builder import _step_criteria
        raw = {
            "steps": [
                {
                    "tool": "container_inspect",
                    "done_when": "artifact_type:thermal_scan",
                    "required_evidence": ["thermal_scan"],
                }
            ]
        }
        result = _step_criteria(raw)
        assert result == {
            "container_inspect": {
                "done_when": "artifact_type:thermal_scan",
                "required_evidence": ["thermal_scan"],
            }
        }

    def test_ignores_non_dict_step_entries(self):
        """T5: Ungültige step-Einträge werden übersprungen."""
        from core.thinking.planner.step_builder import _step_criteria
        raw = {"steps": ["not_a_dict", None, {"tool": "memory_save", "done_when": "file_created"}]}
        result = _step_criteria(raw)
        assert "memory_save" in result
        assert result["memory_save"]["done_when"] == "file_created"

    def test_normalizes_required_evidence_string_to_list(self):
        """T5b: LLM gibt required_evidence als String → wird zu Liste normalisiert, kein Zeichen-Split."""
        from core.thinking.planner.step_builder import _step_criteria
        raw = {
            "steps": [
                {
                    "tool": "container_inspect",
                    "required_evidence": "thermal_scan",  # String statt Liste
                }
            ]
        }
        result = _step_criteria(raw)
        assert result["container_inspect"]["required_evidence"] == ["thermal_scan"]


# ---------------------------------------------------------------------------
# P7: tool_steps mit Completion-Criteria (T6–T8)
# ---------------------------------------------------------------------------


class TestToolStepsCompletionCriteria:
    """T6–T8: tool_steps übergibt done_when/required_evidence an PlanStep."""

    def _raw_with_steps(self, tool: str, done_when: str, required_evidence: list) -> dict:
        return {
            "intent": "test",
            "suggested_tools": [tool],
            "steps": [
                {
                    "tool": tool,
                    "done_when": done_when,
                    "required_evidence": required_evidence,
                }
            ],
        }

    def test_tool_steps_passes_done_when_to_plan_step(self):
        """T6: PlanStep.done_when wird aus raw_plan['steps'] gesetzt."""
        plan = build_plan_from_analysis(
            self._raw_with_steps("container_inspect", "artifact_type:thermal_scan", []),
            user_text="Scan container",
        )
        assert plan.steps[0].done_when == "artifact_type:thermal_scan"

    def test_tool_steps_passes_required_evidence_to_plan_step(self):
        """T7: PlanStep.required_evidence wird aus raw_plan['steps'] gesetzt."""
        plan = build_plan_from_analysis(
            self._raw_with_steps("container_inspect", "", ["thermal_scan"]),
            user_text="Scan container",
        )
        assert plan.steps[0].required_evidence == ["thermal_scan"]

    def test_tool_steps_defaults_when_no_steps_in_raw_plan(self):
        """T8: Ohne 'steps' bleiben done_when='' und required_evidence=[] — Backward-compat."""
        plan = build_plan_from_analysis(
            _raw(intent="inspect", tools=["container_inspect"]),
            user_text="Inspect",
        )
        assert plan.steps[0].done_when == ""
        assert plan.steps[0].required_evidence == []

    def test_tool_steps_passes_fantasy_evidence_type(self):
        """T8b: Fantasy-Typ 'quantum_probe' wird ohne Whitelist-Check durchgereicht."""
        plan = build_plan_from_analysis(
            self._raw_with_steps("some_tool", "artifact_type:quantum_probe", ["quantum_probe"]),
            user_text="Run quantum probe",
        )
        assert plan.steps[0].required_evidence == ["quantum_probe"]
        assert plan.steps[0].done_when == "artifact_type:quantum_probe"


class TestNeedsVisibleProgress:
    """T11: needs_visible_progress aus raw_plan landet in context_hints."""

    def test_needs_visible_progress_true_passed_through(self):
        """T11a: needs_visible_progress=True im raw_plan → context_hints True."""
        plan = build_plan_from_analysis(
            _raw(needs_visible_progress=True),
            user_text="Deploy something",
        )
        assert plan.context_hints["needs_visible_progress"] is True

    def test_needs_visible_progress_false_by_default(self):
        """T11b: Fehlt needs_visible_progress im raw_plan → context_hints False."""
        plan = build_plan_from_analysis(
            _raw(),
            user_text="Deploy something",
        )
        assert plan.context_hints["needs_visible_progress"] is False
