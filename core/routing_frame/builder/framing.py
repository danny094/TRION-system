"""Confidence scoring, dialogue-style mapping, and reasons list for the routing frame.

These three helpers shape the presentation layer of the frame — how
certain the frame is, what conversational style applies, and a
human-readable list of reasons that downstream modules can log.
"""

from __future__ import annotations

from core.classifier.contracts import ClassifierResult


def confidence(
    classifier_result: ClassifierResult,
    dialogue_confidence: float,
    *,
    selected_count: int,
    has_loop_markers: bool,
) -> float:
    value = max(0.0, min(1.0, (float(classifier_result.confidence or 0.0) + float(dialogue_confidence or 0.0)) / 2.0))
    if selected_count:
        value = min(1.0, value + 0.08)
    if has_loop_markers:
        value = min(1.0, value + 0.05)
    return round(value, 3)


def dialogue_style(dialogue_act: str) -> str:
    return {
        "smalltalk": "reflective",
        "feedback": "conversational",
        "analysis": "analysis",
        "ack": "short_ack",
    }.get(str(dialogue_act or "").strip(), "neutral")


def reasons(
    *,
    intent_kind: str,
    domain: str,
    evidence_need: str,
    execution_mode: str,
    has_loop_markers: bool,
    selected_count: int,
) -> list[str]:
    result = [
        f"intent_kind={intent_kind}",
        f"domain={domain}",
        f"evidence_need={evidence_need}",
        f"execution_mode={execution_mode}",
    ]
    if has_loop_markers:
        result.append("loop_markers_present")
    if selected_count:
        result.append(f"selected_tools={selected_count}")
    return result
