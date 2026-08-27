from collections.abc import Mapping
from typing import Any

from config import (
    get_output_multi_tool_synthesis_enable,
    get_output_renderable_evidence_max_bullets_per_item,
    get_output_renderable_evidence_max_items,
)
from core.output.contracts import RenderableEvidence
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff


def build_renderable_evidence(handoff: OutputEvidenceHandoff) -> tuple[RenderableEvidence, ...]:
    if type(handoff) is not OutputEvidenceHandoff:
        raise TypeError("handoff must be OutputEvidenceHandoff")
    items: list[RenderableEvidence] = []
    max_items = get_output_renderable_evidence_max_items()
    for item in handoff.items:
        items.append(_build_item(item.structured_content))
        if len(items) >= max_items:
            break
    return tuple(items)


def render_single_renderable_evidence(items: tuple[RenderableEvidence, ...]) -> str:
    if len(items) != 1:
        return ""
    item = items[0]
    if not item.bullets:
        return item.summary
    return f"{item.summary} Verifizierte Details: {'; '.join(item.bullets)}."


def render_multi_renderable_evidence(items: tuple[RenderableEvidence, ...]) -> str:
    if len(items) <= 1:
        return ""
    if not get_output_multi_tool_synthesis_enable():
        return ""
    lines = ["Verifizierte Ergebnisse:"]
    for item in items[: get_output_renderable_evidence_max_items()]:
        lines.append(f"- {item.summary}")
    return "\n".join(lines)


def _build_item(content: Mapping[str, Any]) -> RenderableEvidence:
    if len(content) == 1:
        summary = f"Verifiziertes Ergebnis: {_value(next(iter(content.values())))}."
        entries: tuple[str, ...] = ()
    else:
        summary = "Verifiziertes Ergebnis ist verfügbar."
        entries = tuple(
            f"{_label(key)}: {_value(value)}"
            for key, value in list(content.items())[: get_output_renderable_evidence_max_bullets_per_item()]
        )
    return RenderableEvidence(summary=summary, bullets=entries)


def _label(value: str) -> str:
    return str(value or "").replace("_", " ").strip().capitalize()


def _value(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        if all(not isinstance(item, (Mapping, list, tuple)) for item in value):
            return ", ".join(_text(item) for item in value[:6] if _text(item))
        return ", ".join(_value(item) for item in value[:4])
    if isinstance(value, Mapping):
        return ", ".join(f"{_label(key)}={_value(item)}" for key, item in value.items())
    return _text(value)


def _text(value: Any) -> str:
    return str(value or "").strip()
