from typing import Any

from core.classifier.contracts import ClassifierResult


def build_fallback_reasoning_text(
    classifier_result: ClassifierResult | None,
    tools: list[str],
    has_memory: bool,
    projection: str,
    derivation: dict[str, Any],
    additional_evidence: dict[str, Any],
) -> str:
    parts = ["Fallback analyzer (LLM analyzer disabled)."]
    if classifier_result:
        parts.append(
            f"Classifier: category={classifier_result.category.value}, "
            f"route={classifier_result.route.value}, pattern={classifier_result.matched_pattern or 'none'}."
        )
    parts.append(f"Resolved tools: {tools or 'none'}.")
    if projection:
        parts.append(f"Response projection: {projection}.")
    if derivation:
        parts.append(f"Response derivation: {derivation.get('kind')}.")
    if additional_evidence:
        parts.append(f"Additional evidence needed: {additional_evidence.get('reason') or additional_evidence.get('kind')}.")
    if has_memory:
        parts.append("Orchestrator delivered memory items — surfacing them.")
    return " ".join(parts)
