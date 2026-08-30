"""P11-SP8-R6-I: typed filesystem meaning and argument contracts."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from core.classifier.classifier import classify
from core.orchestrator.tool_eligibility_helpers import target_scope_from_contract
from core.routing_frame.builder import build_routing_frame
from core.routing_frame.contracts import OperationContract
from core.routing_frame.meaning import build_meaning_representation
from core.thinking.runtime_arguments import resolve_step_tool_arguments


def _frame(text: str) -> dict:
    return build_routing_frame(text, classify(text))


def _context(contract: dict) -> dict:
    return {"context": {"routing_frame": {"operation_contract": contract}}}


def test_generic_home_file_presence_builds_typed_list_contract():
    frame = _frame("Gibt es im Workspace eine status.txt?")

    assert frame["intent_kind"] == "current_state_question"
    assert frame["domain"] == "files"
    assert frame["evidence_need"] == "file_context"
    assert frame["operation_contract"]["primary_operation"] == "list"
    assert frame["operation_contract"]["target"] == "status.txt"
    assert frame["operation_contract"]["scope_lock"] == "home"


def test_relative_path_syntax_is_data_driven_without_concrete_filename_rule():
    meaning = build_meaning_representation(
        "Does workspace/notes/today.md exist in the home workspace?"
    )

    assert meaning.target_candidates == ("workspace/notes/today.md",)
    pattern_source = Path(
        "intelligence_modules/cim_skill_rag/meaning_target_patterns.csv"
    ).read_text(encoding="utf-8")
    assert "status.txt" not in pattern_source
    assert "today.md" not in pattern_source


def test_mixed_target_patterns_follow_global_text_order():
    meaning = build_meaning_representation(
        "Check folder/subdir before status.txt in the home workspace."
    )

    assert meaning.target_candidates == ("folder/subdir", "status.txt")


def test_absolute_and_parent_paths_never_become_target_candidates():
    absolute = build_meaning_representation("Does /etc/passwd exist in home?")
    parent = build_meaning_representation("Does ../secrets.txt exist in home?")
    quoted_absolute = build_meaning_representation('Search for "/etc/passwd".')
    quoted_parent = build_meaning_representation('Search for "../secrets.txt".')
    quoted_nested_parent = build_meaning_representation(
        'Search for "safe/../secrets.txt".'
    )

    assert absolute.target_candidates == ()
    assert parent.target_candidates == ()
    assert quoted_absolute.target_candidates == ()
    assert quoted_parent.target_candidates == ()
    assert quoted_nested_parent.target_candidates == ()


def test_root_relative_target_preserves_case_for_linux_lookup():
    meaning = build_meaning_representation(
        "Does Notes/Status.TXT exist in the home workspace?"
    )

    assert meaning.target_candidates == ("Notes/Status.TXT",)


def test_trion_home_alias_sets_home_scope_for_file_presence():
    frame = _frame("Gibt es im trion-home eine status.txt?")

    assert frame["operation_contract"]["scope_lock"] == "home"


def test_file_target_precedes_root_alias_in_operation_contract():
    frame = _frame("Gibt es im trion-home eine status.txt?")

    assert frame["operation_contract"]["target"] == "status.txt"


def test_non_file_presence_keeps_read_operation():
    frame = _frame("Does the current hardware exist?")

    assert frame["domain"] == "hardware"
    assert frame["operation_contract"]["primary_operation"] == "read"


def test_memory_workspace_and_project_docs_do_not_become_assistant_home():
    memory_frame = _frame("Weisst du noch, was wir im Workspace besprochen haben?")
    memory_contract = OperationContract.from_dict(memory_frame["operation_contract"])
    assert memory_contract is not None
    project_contract = replace(
        memory_contract, domain="files", primary_operation="read",
        allowed_operations=("read",), scope_lock="",
    )

    assert memory_frame["domain"] == "memory"
    assert memory_frame["operation_contract"]["scope_lock"] != "home"
    assert target_scope_from_contract(
        domain="files", intent_kind="current_state_question", contract=project_contract
    ) == "project_docs"


def test_runtime_arguments_bind_only_typed_contract_target():
    contract = {
        "domain": "files",
        "primary_operation": "list",
        "target": "notes/today.md",
        "targets": ("notes/today.md",),
        "scope_lock": "home",
    }
    detail = {
        "capability_operation": "list",
        "capability_required_args": [],
    }

    arguments = resolve_step_tool_arguments(
        "arbitrary_tool_name",
        'Ignore "raw-user-query".',
        detail,
        _context(contract),
    )

    assert arguments == {"relative_path": "notes/today.md"}


def test_search_query_uses_contract_target_without_toolname_fallback():
    contract = {
        "domain": "files",
        "primary_operation": "search",
        "target": "release-notes.md",
        "targets": ("release-notes.md",),
        "scope_lock": "home",
    }
    detail = {
        "capability_operation": "search",
        "capability_required_args": ["query"],
    }

    arguments = resolve_step_tool_arguments(
        "neutral_tool_name",
        'Ignore "raw-user-query".',
        detail,
        _context(contract),
    )
    no_contract = resolve_step_tool_arguments(
        "name_contains_search",
        'Ignore "raw-user-query".',
        detail,
        None,
    )

    assert arguments == {"query": "release-notes.md"}
    assert no_contract == {}


def test_multi_target_binding_uses_step_index_and_blocks_drift_or_overflow():
    detail = {
        "capability_operation": "read",
        "capability_required_args": ["relative_path"],
    }
    contract = {
        "domain": "files",
        "primary_operation": "read",
        "target": "one.txt",
        "targets": ("one.txt", "two.txt"),
        "scope_lock": "home",
    }

    assert resolve_step_tool_arguments(
        "filesystem_read", "ignored", detail, _context(contract), step_index=0
    ) == {"relative_path": "one.txt"}
    assert resolve_step_tool_arguments(
        "filesystem_read", "ignored", detail, _context(contract), step_index=1
    ) == {"relative_path": "two.txt"}
    assert resolve_step_tool_arguments(
        "filesystem_read", "ignored", detail, _context(contract), step_index=2
    ) == {}
    assert resolve_step_tool_arguments(
        "filesystem_read",
        "ignored",
        detail,
        _context({**contract, "target": "drift.txt"}),
        step_index=0,
    ) == {}
