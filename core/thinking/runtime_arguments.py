from __future__ import annotations

import re
from typing import Any, Dict, Mapping

# Synonyme, die auf den verifizierten Home-Container verweisen (kein hardcodierter Tool-Name).
_HOME_TOKENS = frozenset({
    "trion-home", "trion home", "home", "homespace", "zuhause",
    "dieser container", "this container",
})


def resolve_step_tool_arguments(
    tool_name: str,
    user_text: str,
    tool_detail: Mapping[str, Any] | None,
    orchestrator_context: Mapping[str, Any] | None,
    *,
    step_index: int = 0,
) -> Dict[str, Any]:
    detail = tool_detail if isinstance(tool_detail, Mapping) else {}
    required_args = {str(item).strip().lower() for item in detail.get("capability_required_args") or [] if str(item).strip()}
    contract = _operation_contract(orchestrator_context)
    operation = str(contract.get("primary_operation") or "").strip().lower()
    target = _target_for_step(contract, step_index)
    arguments: Dict[str, Any] = {}
    if target and operation == "search" and "query" in required_args:
        arguments["query"] = target
    if target and str(contract.get("domain") or "").strip().lower() == "files":
        if operation in {"list", "read", "inspect"}:
            arguments["relative_path"] = target
    if "container_id_or_name" in required_args:
        home = _get_home_context(orchestrator_context)
        # Shortcut (Doc 36 Regel 3): wenn home_context verifiziert und Text auf Home verweist,
        # container_id direkt auflösen — kein Name-Matching nötig.
        if isinstance(home, Mapping) and home.get("verified") is True and _is_home_reference(user_text):
            resolved = str(home.get("container_id") or "").strip()
            if resolved:
                arguments["container_id"] = resolved
                return arguments
        # Fallback: Name extrahieren und gegen home_context abgleichen.
        container_name = _extract_container_name(user_text)
        if container_name:
            if isinstance(home, Mapping) and str(home.get("container_name") or "").strip() == container_name:
                resolved = str(home.get("container_id") or "").strip()
                if resolved:
                    arguments["container_id"] = resolved
                    return arguments
            arguments["container_id"] = container_name
    return arguments


def _get_home_context(orchestrator_context: Any) -> Any:
    ctx = orchestrator_context or {}
    inner = ctx.get("context") if isinstance(ctx, Mapping) else None
    return inner.get("home_context") if isinstance(inner, Mapping) else None


def _operation_contract(orchestrator_context: Any) -> Mapping[str, Any]:
    if not isinstance(orchestrator_context, Mapping):
        return {}
    direct = orchestrator_context.get("routing_frame")
    if isinstance(direct, Mapping) and isinstance(direct.get("operation_contract"), Mapping):
        return direct["operation_contract"]
    inner = orchestrator_context.get("context")
    if isinstance(inner, Mapping):
        frame = inner.get("routing_frame")
        if isinstance(frame, Mapping) and isinstance(frame.get("operation_contract"), Mapping):
            return frame["operation_contract"]
    return {}


def _target_for_step(contract: Mapping[str, Any], step_index: int) -> str:
    values = contract.get("targets")
    if not isinstance(values, (list, tuple)):
        return ""
    targets = tuple(str(value).strip() for value in values)
    if any(not value for value in targets):
        return ""
    projected = str(contract.get("target") or "").strip()
    if projected != (targets[0] if targets else ""):
        return ""
    if len(targets) <= 1:
        return targets[0] if targets else ""
    return targets[step_index] if 0 <= step_index < len(targets) else ""


def _is_home_reference(text: str) -> bool:
    normalized = _normalize(text)
    return any(tok in normalized for tok in _HOME_TOKENS)


def _extract_container_name(text: str) -> str:
    normalized = _normalize(text)
    if "trion-home" in normalized:
        return "trion-home"
    match = re.search(r"\bcontainer\s+([a-z0-9][a-z0-9._-]*)\b", normalized)
    return str(match.group(1) if match else "").strip()


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())
