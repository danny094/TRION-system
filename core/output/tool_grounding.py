import json
from typing import Any, Dict, List

from core.output.renderable_evidence import build_renderable_evidence, render_single_renderable_evidence


def collect_grounded_tool_results(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    task_loop = context.get("task_loop") if isinstance(context, dict) else None
    artifacts = task_loop.get("artifacts") if isinstance(task_loop, dict) else None
    if not isinstance(artifacts, list):
        return []
    grounded: List[Dict[str, Any]] = []
    for artifact in artifacts:
        result = _grounded_result(artifact)
        if result:
            grounded.append(result)
    return grounded


def _grounded_result(artifact: Any) -> Dict[str, Any]:
    if not isinstance(artifact, dict):
        return {}
    if str(artifact.get("artifact_type") or "") != "tool_result":
        return {}
    parsed = _parse_result(artifact.get("result") or artifact.get("output"))
    if not parsed:
        return {}
    facts = parsed if isinstance(parsed, dict) else {"value": str(parsed)}
    return {
        "tool_name": str(artifact.get("tool") or "").strip(),
        "step_id": str(artifact.get("source_step_id") or artifact.get("step_id") or "").strip(),
        "facts": facts,
    }


def render_single_grounded_tool_result(grounded_results: List[Dict[str, Any]]) -> str:
    return render_single_renderable_evidence(build_renderable_evidence(grounded_results))


def _parse_result(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else text
    except Exception:
        return text
