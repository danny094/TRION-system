from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


def flatten_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out: List[str] = []
        for item in content:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                txt = str(item.get("text") or "")
                if txt:
                    out.append(txt)
        return "".join(out)
    return str(content or "")


def normalize_openai_messages(messages: Iterable[Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role") or "user").strip().lower()
        if role not in {"system", "user", "assistant"}:
            role = "user"
        content = flatten_content(msg.get("content"))
        if content:
            out.append({"role": role, "content": content})
    return out or [{"role": "user", "content": ""}]


def normalize_anthropic_messages(messages: Iterable[Dict[str, Any]]) -> Tuple[str, List[Dict[str, str]]]:
    system_parts: List[str] = []
    out: List[Dict[str, str]] = []
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role") or "user").strip().lower()
        content = flatten_content(msg.get("content"))
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
            continue
        if role not in {"user", "assistant"}:
            role = "user"
        out.append({"role": role, "content": content})
    return "\n\n".join(system_parts).strip(), out or [{"role": "user", "content": ""}]
