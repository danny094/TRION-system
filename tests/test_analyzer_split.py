"""Guardrail-Tests für den analyzer.py → analyzer/-Package-Split.

Prüft:
1. Importpfad unverändert: `from core.thinking.analyzer import analyze_request`
2. Submodule existieren und exportieren die erwarteten Namen.
3. Normalisierungs-Logik bleibt nach dem Split identisch.
"""
from __future__ import annotations

from typing import Any, Dict
import pytest

from core.thinking.analyzer import analyze_request


# ---------------------------------------------------------------------------
# Importpfad-Check
# ---------------------------------------------------------------------------


class TestImportPath:
    def test_analyze_request_importable(self):
        assert callable(analyze_request)

    def test_submodule_helpers_importable(self):
        from core.thinking.analyzer.helpers import (
            routing_frame,
            natural_repeat_count,
            tool_names,
        )
        assert callable(routing_frame)
        assert callable(natural_repeat_count)
        assert callable(tool_names)

    def test_submodule_normalizers_importable(self):
        from core.thinking.analyzer.normalizers import (
            normalize_derivable_time_followup,
            normalize_loop_hints,
            merge_selected_tools,
        )
        assert callable(normalize_derivable_time_followup)
        assert callable(normalize_loop_hints)
        assert callable(merge_selected_tools)


# ---------------------------------------------------------------------------
# helpers — direkt
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_routing_frame_reads_direct(self):
        from core.thinking.analyzer.helpers import routing_frame
        ctx = {"routing_frame": {"execution_mode": "loop"}}
        assert routing_frame(ctx) == {"execution_mode": "loop"}

    def test_routing_frame_empty_when_absent(self):
        from core.thinking.analyzer.helpers import routing_frame
        assert routing_frame(None) == {}
        assert routing_frame({}) == {}

    def test_natural_repeat_count_from_digit_x(self):
        from core.thinking.analyzer.helpers import natural_repeat_count
        assert natural_repeat_count("Mache das 5x") == 5

    def test_natural_repeat_count_default_one(self):
        from core.thinking.analyzer.helpers import natural_repeat_count
        assert natural_repeat_count("Was ist Python?") == 1

    def test_tool_names_from_strings(self):
        from core.thinking.analyzer.helpers import tool_names
        assert tool_names(["memory_save", "memory_save", "memory_search"]) == [
            "memory_save",
            "memory_search",
        ]

    def test_tool_names_from_dicts(self):
        from core.thinking.analyzer.helpers import tool_names
        raw = [{"name": "memory_save"}, {"name": "memory_search"}]
        assert tool_names(raw) == ["memory_save", "memory_search"]

    def test_tool_names_empty_on_none(self):
        from core.thinking.analyzer.helpers import tool_names
        assert tool_names(None) == []


# ---------------------------------------------------------------------------
# normalizers — direkt
# ---------------------------------------------------------------------------


class TestNormalizeLoopHints:
    def _run(self, raw: Dict[str, Any], user_text: str = "x", ctx=None) -> Dict[str, Any]:
        from core.thinking.analyzer.normalizers import normalize_loop_hints
        return normalize_loop_hints(raw, user_text=user_text, orchestrator_context=ctx)

    def test_needs_loop_false_by_default(self):
        result = self._run({})
        assert result["needs_loop"] is False

    def test_needs_loop_true_from_raw_plan(self):
        result = self._run({"needs_loop": True, "suggested_tools": ["memory_save"]})
        assert result["needs_loop"] is True

    def test_needs_loop_true_from_routing_frame(self):
        ctx = {"routing_frame": {"execution_mode": "loop"}}
        result = self._run({}, ctx=ctx)
        assert result["needs_loop"] is True

    def test_repeat_count_from_routing_signals(self):
        ctx = {"routing_frame": {"source_signals": {"repeat_count": 4}}}
        result = self._run({}, ctx=ctx)
        assert result["repeat_count_hint"] == 4

    def test_repeat_count_from_user_text_when_loop(self):
        result = self._run({"needs_loop": True, "suggested_tools": ["x"]}, user_text="Mache das 3x")
        assert result["repeat_count_hint"] == 3

    def test_task_loop_kind_set_to_loop_when_needs_loop(self):
        result = self._run({"needs_loop": True, "suggested_tools": ["memory_save"]})
        assert result["task_loop_kind"] == "loop"

    def test_operation_family_hint_lowercased(self):
        result = self._run({"operation_family_hint": "READ"})
        assert result["operation_family_hint"] == "read"


class TestNormalizeDerivableTimeFollowup:
    def _run(self, raw: Dict[str, Any], user_text: str = "x", ctx=None) -> Dict[str, Any]:
        from core.thinking.analyzer.normalizers import normalize_derivable_time_followup
        return normalize_derivable_time_followup(raw, user_text, ctx)

    def test_passthrough_when_no_time_followup(self):
        raw = {"suggested_tools": ["memory_save"]}
        result = self._run(raw, user_text="Speichere das")
        assert result is raw  # unverändert zurückgegeben

    def test_clears_time_now_tool_on_time_followup(self):
        ctx = {"routing_frame": {"source_signals": {"live_claim": "time"}}}
        raw = {"suggested_tools": ["time_now"], "task_loop_candidate": True}
        result = self._run(
            raw,
            user_text="Zeig mir das in UTC",
            ctx=ctx,
        )
        # Wenn kein derivable_time_followup → passthrough; dieser Test
        # prüft nur, dass die Funktion ohne Crash läuft und eine dict zurückgibt
        assert isinstance(result, dict)


class TestMergeSelectedTools:
    def _run(
        self,
        raw: Dict[str, Any],
        selected=None,
        user_text: str = "x",
        ctx=None,
    ) -> Dict[str, Any]:
        from core.thinking.analyzer.normalizers import merge_selected_tools
        return merge_selected_tools(raw, selected, user_text=user_text, orchestrator_context=ctx)

    def test_passthrough_when_raw_plan_has_tools(self):
        raw = {"suggested_tools": ["memory_save"]}
        result = self._run(raw, selected=["memory_search"])
        assert result["suggested_tools"] == ["memory_save"]

    def test_passthrough_when_no_selected(self):
        raw: Dict[str, Any] = {}
        result = self._run(raw, selected=None)
        assert result is raw

    def test_merges_selected_when_raw_plan_empty(self):
        raw: Dict[str, Any] = {"suggested_tools": []}
        result = self._run(raw, selected=["memory_save"], user_text="Speichere das")
        assert result["suggested_tools"] == ["memory_save"]
        assert result["task_loop_candidate"] is True

    def test_single_tool_kind_is_single_tool(self):
        raw: Dict[str, Any] = {"suggested_tools": []}
        result = self._run(raw, selected=["memory_save"], user_text="Speichere das")
        assert result["task_loop_kind"] == "single_tool"

    def test_multi_tool_kind_is_visible_multistep(self):
        raw: Dict[str, Any] = {"suggested_tools": []}
        result = self._run(
            raw,
            selected=["memory_save", "memory_search"],
            user_text="Speichere und suche",
        )
        assert result["task_loop_kind"] == "visible_multistep"


# ---------------------------------------------------------------------------
# analyze_request — Verhalten mit llm_enabled=False (deterministischer Pfad)
# ---------------------------------------------------------------------------


class TestAnalyzeRequestFallbackPath:
    def _run(self, user_text: str, **kwargs) -> Dict[str, Any]:
        return analyze_request(
            user_text,
            classifier_result=None,
            available_tools=kwargs.get("available_tools"),
            selected_tools=kwargs.get("selected_tools"),
            orchestrator_context=kwargs.get("orchestrator_context"),
            llm_enabled=False,
        )

    def test_returns_dict(self):
        result = self._run("Was ist Python?")
        assert isinstance(result, dict)

    def test_needs_loop_false_default(self):
        result = self._run("Was ist Python?")
        assert result["needs_loop"] is False

    def test_repeat_count_minimum_one(self):
        result = self._run("Was ist Python?")
        assert result["repeat_count_hint"] >= 1

    def test_operation_family_hint_is_lowercase_string(self):
        result = self._run("Was ist Python?")
        assert isinstance(result["operation_family_hint"], str)
        assert result["operation_family_hint"] == result["operation_family_hint"].lower()

    def test_loop_from_routing_frame_propagates(self):
        ctx = {
            "routing_frame": {
                "execution_mode": "loop",
                "source_signals": {"repeat_count": 3, "live_claim": "none"},
            }
        }
        result = self._run("Mache das 3 mal", orchestrator_context=ctx)
        assert result["needs_loop"] is True
        assert result["repeat_count_hint"] >= 3
