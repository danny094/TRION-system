"""Baut PlanStep-Objekte aus raw_plan und suggested_tools.

Keine Tool-Auflösung, keine Metadaten — nur Step-Konstruktion.
"""
from __future__ import annotations

from typing import Any, Dict

from core.input_processor.contracts import DocumentContext
from core.routing_frame.contracts import OperationContract
from core.thinking.contracts import PlanStep, RiskLevel
from core.thinking.document_steps import build_document_steps
from core.thinking.planner.frame_reader import (
    needs_loop,
    repeat_count,
    routing_frame,
    selected_tool_detail,
)
from core.thinking.planner.plan_meta import risk_level
from core.thinking.runtime_arguments import resolve_step_tool_arguments


def build_steps(
    raw_plan: Dict[str, Any],
    user_text: str,
    suggested_tools: list[str],
    document_context: DocumentContext | None,
    orchestrator_context: Dict[str, Any] | None,
) -> list[PlanStep]:
    risk = risk_level(raw_plan)
    if not suggested_tools:
        return [
            PlanStep(
                step_id="answer_user",
                title="Answer user",
                goal="Generate a direct answer to the latest user message.",
                tool=None,
                risk=risk,
            )
        ]
    retrieval_steps = build_document_steps(
        raw_plan, user_text, suggested_tools, document_context, risk
    )
    if retrieval_steps:
        return retrieval_steps
    return tool_steps(raw_plan, user_text, suggested_tools, orchestrator_context, risk)


def _step_criteria(raw_plan: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extrahiert done_when/required_evidence per Tool aus raw_plan['steps'].

    Gibt leeres Dict zurück wenn kein 'steps'-Feld vorhanden — Backward-compat.
    Kein Hardcoding von Tool-Namen oder Evidence-Typen; rein generisch.
    """
    result: Dict[str, Dict[str, Any]] = {}
    for step_raw in raw_plan.get("steps") or []:
        if not isinstance(step_raw, dict):
            continue
        tool = str(step_raw.get("tool") or "").strip()
        if not tool:
            continue
        raw_ev = step_raw.get("required_evidence") or []
        if isinstance(raw_ev, str):
            # LLM gibt manchmal String statt Liste — normalisieren
            raw_ev = [raw_ev] if raw_ev.strip() else []
        result[tool] = {
            "done_when": str(step_raw.get("done_when") or "").strip(),
            "required_evidence": [str(e) for e in raw_ev if str(e).strip()],
        }
    return result


def _authoritative_criteria(
    tool_name: str,
    frame: Dict[str, Any],
    tool_detail: Dict[str, Any],
    fallback: Dict[str, Any],
) -> Dict[str, Any]:
    contract = OperationContract.from_dict(frame.get("operation_contract"))
    if contract is None:
        return fallback
    required = list(contract.required_evidence)
    declared: set[str] = set()
    if str(tool_detail.get("name") or "").strip() == tool_name:
        declared = {
            str(item).strip()
            for item in list(tool_detail.get("capability_evidence_types") or [])
            if str(item).strip()
        }
    if required and not all(item in declared for item in required):
        return {
            "done_when": "",
            "required_evidence": required,
        }
    return {
        "done_when": f"artifact_type:{required[0]}" if required else "",
        "required_evidence": required,
    }


def tool_steps(
    raw_plan: Dict[str, Any],
    user_text: str,
    suggested_tools: list[str],
    orchestrator_context: Dict[str, Any] | None,
    risk: RiskLevel,
) -> list[PlanStep]:
    frame = routing_frame(orchestrator_context)
    loop = needs_loop(raw_plan, orchestrator_context)
    count = repeat_count(raw_plan, frame)
    goal = str(raw_plan.get("intent") or user_text or "").strip()
    criteria = _step_criteria(raw_plan)
    if loop and len(suggested_tools) == 1 and count > 1:
        tool = suggested_tools[0]
        detail = selected_tool_detail(tool, orchestrator_context)
        crit = _authoritative_criteria(tool, frame, detail, criteria.get(tool, {}))
        return [
            PlanStep(
                step_id=f"tool_{index}",
                title=f"Attempt {index}: Use {tool}",
                goal=goal or f"Use {tool}",
                tool=tool,
                tool_arguments=resolve_step_tool_arguments(
                    tool,
                    user_text,
                    detail,
                    orchestrator_context,
                    step_index=index - 1,
                ),
                risk=risk,
                done_when=crit.get("done_when", ""),
                required_evidence=crit.get("required_evidence", []),
            )
            for index in range(1, count + 1)
        ]
    steps: list[PlanStep] = []
    for index, tool in enumerate(suggested_tools, start=1):
        detail = selected_tool_detail(tool, orchestrator_context)
        crit = _authoritative_criteria(tool, frame, detail, criteria.get(tool, {}))
        steps.append(
            PlanStep(
                step_id=f"tool_{index}",
                title=f"Use {tool}",
                goal=goal or f"Use {tool}",
                tool=tool,
                tool_arguments=resolve_step_tool_arguments(
                    tool,
                    user_text,
                    detail,
                    orchestrator_context,
                    step_index=index - 1,
                ),
                risk=risk,
                done_when=crit.get("done_when", ""),
                required_evidence=crit.get("required_evidence", []),
            )
        )
    return steps
