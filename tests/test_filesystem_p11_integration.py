"""P11-SP8-R6-I: natural prompt to executable filesystem tool."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import re

from core.classifier.classifier import classify
from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_eligibility import eligible_tools_for_contract
from core.routing_frame.builder import build_routing_frame
from core.task_loop.contracts import EvidenceArtifact
from core.task_loop.executable_now import check_executable_now
from core.task_loop.outcome_evaluator import OutcomeAction, evaluate
from core.task_loop.tool_execution_contracts import TaskToolCall
from core.thinking.planner import build_plan_from_analysis
from core.thinking.runtime_arguments import resolve_step_tool_arguments


PROMPT = "Kannst du kurz prüfen, ob es im Workspace eine status.txt gibt?"


def _filesystem_list() -> ToolDescriptor:
    return ToolDescriptor(
        name="filesystem_list",
        capability_domain="files",
        capability_operation="list",
        capability_evidence_types=["file_context"],
        capability_required_args=[],
        capability_risk="read_only",
        capability_target_scopes=["assistant_home"],
    )


def _memory_workspace() -> ToolDescriptor:
    return ToolDescriptor(
        name="workspace_list",
        capability_domain="memory",
        capability_operation="list",
        capability_evidence_types=["memory_context"],
        capability_required_args=[],
        capability_risk="read_only",
        capability_target_scopes=["project_docs"],
    )


def test_natural_workspace_presence_prompt_reaches_executable_filesystem_list():
    frame = build_routing_frame(PROMPT, classify(PROMPT))
    contract = frame["operation_contract"]
    filesystem = _filesystem_list()

    eligible = eligible_tools_for_contract(
        [filesystem, _memory_workspace()],
        contract,
    )
    detail = asdict(filesystem)
    arguments = resolve_step_tool_arguments(
        filesystem.name,
        PROMPT,
        detail,
        {"routing_frame": frame},
    )
    decision = check_executable_now(
        TaskToolCall(tool_name=filesystem.name, arguments=arguments),
        {filesystem.name: detail},
    )

    assert frame["intent_kind"] == "current_state_question"
    assert frame["domain"] == "files"
    assert frame["evidence_need"] == "file_context"
    assert contract["primary_operation"] == "list"
    assert contract["target"] == "status.txt"
    assert contract["scope_lock"] == "home"
    assert [tool.name for tool in eligible] == ["filesystem_list"]
    assert arguments == {"relative_path": "status.txt"}
    assert decision.allowed is True


def test_workspace_plan_projects_completion_from_operation_contract():
    frame = build_routing_frame(PROMPT, classify(PROMPT))
    filesystem = _filesystem_list()
    raw_plan = {
        "intent": "check workspace file",
        "suggested_tools": [filesystem.name],
        "steps": [
            {
                "tool": filesystem.name,
                "done_when": "artifact_type:memory_context",
                "required_evidence": ["memory_context"],
            }
        ],
    }

    plan = build_plan_from_analysis(
        raw_plan,
        user_text=PROMPT,
        orchestrator_context={
            "routing_frame": frame,
            "selected_tool_details": [asdict(filesystem)],
        },
    )

    assert plan.steps[0].required_evidence == ["file_context"]
    assert plan.steps[0].done_when == "artifact_type:file_context"
    fingerprint = frame["operation_contract_fingerprint"]
    decision = evaluate(
        plan,
        [EvidenceArtifact(
            step_id=plan.steps[0].step_id,
            artifact_type="file_context",
            metadata={
                "validated_evidence": True,
                "operation_contract_fingerprint": fingerprint,
            },
        )],
        replan_budget_remaining=False,
        expected_operation_contract_fingerprint=fingerprint,
    )
    assert decision.action is OutcomeAction.COMPLETE


def test_admin_runtime_mounts_trion_home_read_only_with_exact_root():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^  trion-admin-api:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:\n|\Z)",
        compose,
    )
    assert match is not None
    admin = match.group("body")

    assert "TRION_FILESYSTEM_ROOT: /trion-home" in admin
    assert "- trion-home:/trion-home:ro" in admin
    assert "- trion-home:/trion-home\n" not in admin


def test_home_owner_retains_read_write_mount_and_initializes_owned_files():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^  trion-home:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:\n|^volumes:\n|\Z)",
        compose,
    )
    assert match is not None
    home = match.group("body")

    assert "- trion-home:/home/trion" in home
    assert "- trion-home:/home/trion:ro" not in home
    assert "> /home/trion/.trion/home.json" in home
    assert '> /home/trion/status.txt' in home


def test_admin_entrypoint_does_not_prepare_read_only_trion_home_as_writable():
    entrypoint = Path("adapters/admin-api/docker-entrypoint.sh").read_text(
        encoding="utf-8",
    )

    assert "TRION_HOME_DIR" not in entrypoint
    assert "/trion-home" not in entrypoint
