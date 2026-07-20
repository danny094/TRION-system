import json
from typing import Any, Dict, Iterable, List


def resolve_tool_arguments(arguments: Dict[str, Any], artifacts: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    raw = dict(arguments or {})
    if "document_source_step" not in raw:
        return raw
    source_step = str(raw.get("document_source_step") or "").strip()
    rank = max(0, int(raw.get("document_result_rank") or 0))
    fallback_entry_id = int(raw.get("document_fallback_entry_id") or raw.get("entry_id") or 0)
    resolved_entry_id = _workspace_entry_id_from_artifacts(artifacts, source_step, rank)
    if resolved_entry_id <= 0:
        resolved_entry_id = fallback_entry_id
    return {
        key: value
        for key, value in {
            **raw,
            "entry_id": resolved_entry_id,
        }.items()
        if key not in {"document_source_step", "document_result_rank", "document_fallback_entry_id"}
    }


def collect_result_artifacts(
    tool_name: str,
    step_id: str,
    output: Dict[str, Any],
    base_artifacts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    artifacts = [*list(base_artifacts or []), _tool_result_artifact(tool_name, step_id, output)]
    if tool_name != "memory_semantic_search":
        return artifacts
    for rank, result in enumerate(output.get("results") or []):
        workspace_entry_id = _workspace_entry_id_from_result(result)
        if workspace_entry_id <= 0:
            continue
        artifacts.append(
            {
                "id": f"{step_id}-semantic-{rank}",
                "artifact_type": "semantic_search_result",
                "tool": tool_name,
                "source_step_id": step_id,
                "rank": rank,
                "workspace_entry_id": workspace_entry_id,
                "similarity": result.get("similarity"),
            }
        )
    return artifacts


def _tool_result_artifact(tool_name: str, step_id: str, output: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": f"{step_id}-result",
        "artifact_type": "tool_result",
        "tool": tool_name,
        "source_step_id": step_id,
        "result": _serialize_output(output),
        "output": _serialize_output(output),
    }


def _serialize_output(output: Dict[str, Any]) -> str:
    try:
        return json.dumps(output, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(output)


def _workspace_entry_id_from_artifacts(artifacts: Iterable[Dict[str, Any]], source_step: str, rank: int) -> int:
    for artifact in artifacts:
        if str(artifact.get("artifact_type") or "") != "semantic_search_result":
            continue
        if str(artifact.get("source_step_id") or "") != source_step:
            continue
        artifact_rank = artifact.get("rank")
        if artifact_rank is None or int(artifact_rank) != rank:
            continue
        return int(artifact.get("workspace_entry_id") or 0)
    return 0


def _workspace_entry_id_from_result(result: Dict[str, Any]) -> int:
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    direct = int(metadata.get("workspace_entry_id") or result.get("workspace_entry_id") or 0)
    if direct > 0:
        return direct
    value = str(metadata.get("value") or "")
    for part in value.split(";"):
        name, _, raw_value = part.partition(":")
        if name.strip() != "workspace_entry_id":
            continue
        try:
            return int(raw_value.strip() or 0)
        except ValueError:
            return 0
    return 0
