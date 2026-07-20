"""Unit-Tests fuer core.pipeline.orchestrator_stage.replan_tools_from_context()
und replan_tools_with_provenance().

Reproduziert den von Codex gefundenen P1-Bug: eine leere, aber vom Orchestrator
bereits gefilterte Tool-Liste (available_tool_details == []) ist eine gueltige
Tool-Wahrheit (z.B. "alles war forbidden_direct") und darf NICHT durch die
rohen, ungefilterten Tools ersetzt werden. Fallback gilt nur, wenn der
Orchestrator-Block oder der Key darin tatsaechlich fehlt.

P11 SP3-F Fund C (Danny-DECIDE: Option 1 - Markieren statt umbenennen):
replan_tools_from_context() allein macht nicht sichtbar, ob die zurueckgegebene
Liste orchestrator-gefiltert oder roher Fallback ist - beide laufen unter
demselben Namen weiter. replan_tools_with_provenance() liefert zusaetzlich die
Quelle (TOOL_TRUTH_ORCHESTRATOR_FILTERED / TOOL_TRUTH_FALLBACK), ohne
replan_tools_from_context() oder seine Aufrufer umzubenennen.
"""
from __future__ import annotations

from core.pipeline.orchestrator_stage import (
    TOOL_TRUTH_FALLBACK,
    TOOL_TRUTH_ORCHESTRATOR_FILTERED,
    replan_tools_from_context,
    replan_tools_with_provenance,
)

RAW_FALLBACK = [{"name": "graph_find_duplicate_nodes"}]


def test_empty_filtered_list_is_returned_as_is_not_replaced_by_fallback():
    context = {"orchestrator": {"available_tool_details": []}}
    result = replan_tools_from_context(context, RAW_FALLBACK)
    assert result == [], (
        "Eine leere available_tool_details-Liste ist gueltige Tool-Wahrheit "
        "(z.B. alles forbidden_direct) und darf nicht auf die rohen Tools "
        "zurueckfallen."
    )


def test_non_empty_filtered_list_is_passed_through_unchanged():
    filtered = [{"name": "memory_save"}]
    context = {"orchestrator": {"available_tool_details": filtered}}
    result = replan_tools_from_context(context, RAW_FALLBACK)
    assert result == filtered


def test_missing_orchestrator_block_falls_back_to_raw_tools():
    result = replan_tools_from_context({}, RAW_FALLBACK)
    assert result == RAW_FALLBACK


def test_missing_available_tool_details_key_falls_back_to_raw_tools():
    context = {"orchestrator": {"some_other_key": True}}
    result = replan_tools_from_context(context, RAW_FALLBACK)
    assert result == RAW_FALLBACK


def test_non_dict_context_falls_back_to_raw_tools():
    result = replan_tools_from_context(None, RAW_FALLBACK)
    assert result == RAW_FALLBACK


def test_provenance_marks_empty_filtered_list_as_orchestrator_filtered():
    context = {"orchestrator": {"available_tool_details": []}}
    tools, source = replan_tools_with_provenance(context, RAW_FALLBACK)
    assert tools == []
    assert source == TOOL_TRUTH_ORCHESTRATOR_FILTERED


def test_provenance_marks_non_empty_filtered_list_as_orchestrator_filtered():
    filtered = [{"name": "memory_save"}]
    context = {"orchestrator": {"available_tool_details": filtered}}
    tools, source = replan_tools_with_provenance(context, RAW_FALLBACK)
    assert tools == filtered
    assert source == TOOL_TRUTH_ORCHESTRATOR_FILTERED


def test_provenance_marks_missing_block_as_fallback():
    tools, source = replan_tools_with_provenance({}, RAW_FALLBACK)
    assert tools == RAW_FALLBACK
    assert source == TOOL_TRUTH_FALLBACK


def test_provenance_marks_missing_available_tool_details_key_as_fallback():
    context = {"orchestrator": {"some_other_key": True}}
    tools, source = replan_tools_with_provenance(context, RAW_FALLBACK)
    assert tools == RAW_FALLBACK
    assert source == TOOL_TRUTH_FALLBACK


def test_provenance_marks_non_dict_context_as_fallback():
    tools, source = replan_tools_with_provenance(None, RAW_FALLBACK)
    assert tools == RAW_FALLBACK
    assert source == TOOL_TRUTH_FALLBACK


def test_replan_tools_from_context_stays_backward_compatible_with_provenance():
    """replan_tools_from_context() muss exakt den tools-Teil von
    replan_tools_with_provenance() liefern - keine Verhaltensaenderung fuer
    bestehende Aufrufer (runner.py-Vertrag bleibt erhalten)."""
    for context in (
        {"orchestrator": {"available_tool_details": []}},
        {"orchestrator": {"available_tool_details": [{"name": "memory_save"}]}},
        {},
        {"orchestrator": {"some_other_key": True}},
        None,
    ):
        tools, _source = replan_tools_with_provenance(context, RAW_FALLBACK)
        assert replan_tools_from_context(context, RAW_FALLBACK) == tools
