from typing import Any, Mapping

from core.task_loop.tool_execution_contracts import TaskStructuralValidationStatus


def validated_evidence_artifacts(
    *,
    tool_name: str,
    step_id: str,
    output: Mapping[str, Any],
    tool_detail: Mapping[str, Any] | None,
    structural_result: object | None,
    structural_validation_status: TaskStructuralValidationStatus = TaskStructuralValidationStatus.MISSING,
    operation_contract_fingerprint: str | None = None,
) -> list[dict[str, Any]]:
    if structural_validation_status is not TaskStructuralValidationStatus.VALID or structural_result is None:
        return []
    evidence_types = _evidence_types(tool_detail)
    if not evidence_types:
        return []
    fingerprint = str(operation_contract_fingerprint or "").strip()
    return [
        {
            "id": f"{step_id}-evidence-{evidence_type}",
            "artifact_type": evidence_type,
            "tool": tool_name,
            "source_step_id": step_id,
            "content": output,
            "metadata": _metadata(fingerprint),
        }
        for evidence_type in evidence_types
    ]


def _evidence_types(tool_detail: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(tool_detail, Mapping):
        return []
    return [
        str(item).strip()
        for item in list(tool_detail.get("capability_evidence_types") or [])
        if str(item).strip()
    ]


def _metadata(operation_contract_fingerprint: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "validated_evidence": True,
        "legacy_tool_result": False,
    }
    if operation_contract_fingerprint:
        metadata["operation_contract_fingerprint"] = operation_contract_fingerprint
    return metadata
