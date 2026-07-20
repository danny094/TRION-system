import json
from typing import Any, Iterable, List

from config import (
    get_output_multi_tool_synthesis_enable,
    get_output_renderable_evidence_max_bullets_per_item,
    get_output_renderable_evidence_max_items,
)
from core.output.contracts import RenderableEvidence


def build_renderable_evidence(grounded_results: Iterable[dict[str, Any]]) -> List[RenderableEvidence]:
    items: List[RenderableEvidence] = []
    max_items = get_output_renderable_evidence_max_items()
    for item in grounded_results:
        evidence = _build_item(item if isinstance(item, dict) else {})
        if evidence:
            items.append(evidence)
        if len(items) >= max_items:
            break
    return items


def render_single_renderable_evidence(items: List[RenderableEvidence]) -> str:
    if len(items) != 1:
        return ""
    item = items[0]
    if item.tool_name in {"time_now", "container_list"}:
        return item.summary
    if item.tool_name == "memory_graph_search":
        if not item.bullets:
            return item.summary
        return f"{item.summary}\n" + "\n".join(f"- {bullet}" for bullet in item.bullets)
    details = [str(bullet or "").strip() for bullet in item.bullets if str(bullet or "").strip()]
    if not details:
        return item.summary
    return f"{item.summary} Verifizierte Details: {'; '.join(details)}."


def render_multi_renderable_evidence(items: List[RenderableEvidence]) -> str:
    if len(items) <= 1:
        return ""
    if not get_output_multi_tool_synthesis_enable():
        return ""
    lines = ["Verifizierte Ergebnisse:"]
    for item in items[: get_output_renderable_evidence_max_items()]:
        lines.append(f"- {item.summary}")
    return "\n".join(lines)


def _build_item(item: dict[str, Any]) -> RenderableEvidence | None:
    tool_name = str(item.get("tool_name") or "").strip()
    facts = item.get("facts") if isinstance(item.get("facts"), dict) else {}
    if not tool_name or not facts:
        return None
    if tool_name == "time_now":
        return _time_now(tool_name, facts)
    if tool_name == "container_list":
        return _container_list(tool_name, facts)
    if tool_name == "memory_graph_search":
        return _memory_graph_search(tool_name, facts)
    return _generic(tool_name, facts)


def _time_now(tool_name: str, facts: dict[str, Any]) -> RenderableEvidence:
    time_value = _text(facts.get("time"))
    timezone = _text(facts.get("timezone"))
    date_value = _text(facts.get("date"))
    utc_iso = _text(facts.get("utc_iso"))
    summary = "Die aktuelle Uhrzeit ist verifiziert."
    if time_value and timezone:
        summary = f"Es ist {time_value} {timezone}."
    elif time_value:
        summary = f"Es ist {time_value}."
    bullets = []
    if date_value:
        bullets.append(f"Datum: {date_value}")
    if utc_iso:
        bullets.append(f"UTC ISO: {utc_iso}")
    return RenderableEvidence(tool_name=tool_name, summary=summary, bullets=bullets, facts=facts)


def _container_list(tool_name: str, facts: dict[str, Any]) -> RenderableEvidence:
    containers = facts.get("containers") if isinstance(facts.get("containers"), list) else []
    rows = [item for item in containers if isinstance(item, dict)]
    running = [row for row in rows if str(row.get("status") or "").strip().lower() == "running"]
    if running:
        summary = f"Aktuell laufen {len(running)} Container: {_join_names(running)}."
        bullets = [_container_label(row) for row in running[:8]]
    elif rows:
        summary = f"Es sind {len(rows)} Container bekannt, aber aktuell laeuft keiner."
        bullets = [_container_label(row) for row in rows[:8]]
    else:
        summary = "Aktuell laufen keine Container."
        bullets = []
    return RenderableEvidence(tool_name=tool_name, summary=summary, bullets=bullets, facts=facts)


def _memory_graph_search(tool_name: str, facts: dict[str, Any]) -> RenderableEvidence:
    results = facts.get("results") if isinstance(facts.get("results"), list) else []
    rows = [item for item in results if isinstance(item, dict)]
    count = int(facts.get("count") or len(rows) or 0)
    if count <= 0 or not rows:
        return RenderableEvidence(
            tool_name=tool_name,
            summary="Ich habe keinen passenden Memory-Treffer gefunden.",
            bullets=[],
            facts=facts,
        )
    bullets = [_memory_hit_label(row) for row in rows[: get_output_renderable_evidence_max_bullets_per_item()]]
    summary = f"Ich habe {count} passenden Memory-Treffer gefunden." if count == 1 else f"Ich habe {count} passende Memory-Treffer gefunden."
    return RenderableEvidence(tool_name=tool_name, summary=summary, bullets=bullets, facts=facts)


def _generic(tool_name: str, facts: dict[str, Any]) -> RenderableEvidence:
    bullets = []
    for key, value in list(facts.items())[: get_output_renderable_evidence_max_bullets_per_item()]:
        bullets.append(f"{_label(key)}: {_value(value)}")
    summary = "Verifiziertes Tool-Ergebnis ist verfügbar."
    if len(facts) == 1:
        only_value = _value(next(iter(facts.values())))
        summary = f"Verifiziertes Ergebnis: {only_value}."
    return RenderableEvidence(tool_name=tool_name, summary=summary, bullets=bullets, facts=facts)


def _memory_hit_label(row: dict[str, Any]) -> str:
    kind = _text(row.get("type")) or "entry"
    content = " ".join(_text(row.get("content")).split())
    if len(content) > 220:
        content = content[:217].rstrip() + "..."
    if content:
        return f"{_label(kind)}: {content}"
    return _label(kind)


def _join_names(rows: list[dict[str, Any]]) -> str:
    names = [_text(row.get("name")) or "unbenannt" for row in rows[:8]]
    if not names:
        return "keine"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} und {names[1]}"
    return f"{', '.join(names[:-1])} und {names[-1]}"


def _container_label(row: dict[str, Any]) -> str:
    name = _text(row.get("name")) or "unbenannt"
    status = _text(row.get("status")) or "unbekannt"
    image = _text(row.get("image"))
    label = f"{name} ({status})"
    if image:
        label += f" – Image: {image}"
    return label


def _label(value: str) -> str:
    return str(value or "").replace("_", " ").strip().capitalize()


def _value(value: Any) -> str:
    if isinstance(value, list):
        if all(not isinstance(item, (dict, list)) for item in value):
            return ", ".join(_text(item) for item in value[:6] if _text(item))
        return json.dumps(value[:4], ensure_ascii=True)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=True)
    return _text(value)


def _text(value: Any) -> str:
    return str(value or "").strip()
