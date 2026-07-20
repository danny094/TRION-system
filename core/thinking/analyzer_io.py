import asyncio
import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable, Dict

CompletePromptFn = Callable[..., Awaitable[str]]


def invoke_prompt(complete_prompt_fn: CompletePromptFn, **kwargs: Any) -> str:
    result = complete_prompt_fn(**kwargs)
    if not asyncio.iscoroutine(result):
        return str(result or "")
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return str(asyncio.run(result) or "")
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: asyncio.run(result))
        return str(future.result() or "")


def parse_json_object(raw: Any) -> Dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    for candidate in (text, _extract_fenced_json(text), _extract_braced_json(text)):
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _extract_fenced_json(text: str) -> str:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    return match.group(1) if match else ""


def _extract_braced_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    return text[start : end + 1] if start >= 0 and end > start else ""
