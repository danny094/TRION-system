"""Einfache Metadaten-Extraktion aus raw_plan.

Keine Kontext-Logik, keine Step-Logik — nur Wert-Extraktion und Typ-Konversion.
"""
from __future__ import annotations

import re
from typing import Any, Dict

from core.thinking.contracts import (
    AdditionalEvidenceNeed,
    ResponseDerivation,
    ResponseProjection,
    RiskLevel,
)


def risk_level(raw_plan: Dict[str, Any]) -> RiskLevel:
    return (
        RiskLevel.NEEDS_CONFIRMATION
        if str(raw_plan.get("hallucination_risk") or "").strip().lower() == "high"
        else RiskLevel.SAFE
    )


def plan_id(raw_plan: Dict[str, Any], suggested_tools: list[str]) -> str:
    intent = str(raw_plan.get("intent") or "thinking-plan").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", intent).strip("-") or "thinking-plan"
    return f"{slug}-{len(suggested_tools)}-tools" if suggested_tools else slug


def response_projection(raw_plan: Dict[str, Any]) -> ResponseProjection | None:
    kind = str(raw_plan.get("response_projection") or "").strip()
    return ResponseProjection(kind=kind) if kind else None


def response_derivation(raw_plan: Dict[str, Any]) -> ResponseDerivation | None:
    payload = raw_plan.get("response_derivation")
    if not isinstance(payload, dict):
        return None
    kind = str(payload.get("kind") or "").strip()
    if not kind:
        return None
    return ResponseDerivation(kind=kind, seconds=int(payload.get("seconds") or 0))


def additional_evidence_need(raw_plan: Dict[str, Any]) -> AdditionalEvidenceNeed | None:
    payload = raw_plan.get("additional_evidence_needed")
    if not isinstance(payload, dict):
        return None
    kind = str(payload.get("kind") or "").strip()
    if not kind:
        return None
    tools = payload.get("candidate_tools")
    candidates = (
        [str(item).strip() for item in tools if str(item).strip()]
        if isinstance(tools, list)
        else []
    )
    return AdditionalEvidenceNeed(
        kind=kind,
        reason=str(payload.get("reason") or "").strip(),
        candidate_tools=candidates,
    )
