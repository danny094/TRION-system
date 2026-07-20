"""Helper fuer Orchestrator-Tool-Eligibility und Legacy-Projektionen.

SP3-Q/SP3-U: Die von T_eligible produktiv genutzten Helper liegen hier; die
alte Capability-Spec-Schicht wurde entfernt.
"""
from __future__ import annotations

from core.orchestrator.contracts import ToolDescriptor


def capability_operation_family(operation: str) -> str:
    value = str(operation or "").strip().lower()
    if value in {"search", "semantic_search", "graph_search", "recall", "query", "find"}:
        return "search"
    if value in {"read", "get", "load", "recent"}:
        return "read"
    if value in {"list", "inventory"}:
        return "list"
    if value in {"inspect", "describe", "metadata"}:
        return "inspect"
    if value in {"logs", "tail"}:
        return "logs"
    if value in {"save", "create", "write", "record"}:
        return "write"
    if value in {"update", "upsert", "append"}:
        return "update"
    if value in {"delete", "remove", "reset"}:
        return "delete"
    if value in {"start", "stop", "restart", "run", "execute"}:
        return "execute"
    if value in {"maintenance", "maintain", "backfill", "optimize"}:
        return "maintain"
    if value in {"healthcheck", "stats", "status", "neighbors"}:
        return "read"
    return value


def infer_tool_domain(tool: ToolDescriptor) -> str:
    explicit = str(tool.capability_domain or "").strip().lower()
    if explicit:
        return explicit
    haystack = _tool_haystack(tool)
    if any(token in haystack for token in ("memory", "workspace", "conversation_meta", "secret_", "skill_metric", "graph_")):
        return "memory"
    if any(token in haystack for token in ("container", "blueprint")):
        return "container_runtime"
    if "time" in haystack or "clock" in haystack:
        return "time"
    if "file" in haystack or "document" in haystack:
        return "files"
    return ""


def infer_tool_operation_family(tool: ToolDescriptor) -> str:
    explicit = capability_operation_family(str(tool.capability_operation or "").strip().lower())
    if explicit:
        return explicit
    haystack = _tool_haystack(tool)
    if any(token in haystack for token in ("create", "erstellt", "erstellen", "anlegen", "add node", "add_node", "save", "store", "record")):
        return "write"
    if any(token in haystack for token in ("update", "aktualis", "upsert", "append")):
        return "update"
    if any(token in haystack for token in ("delete", "remove", "reset", "lösch", "loesch", "entfern")):
        return "delete"
    if any(token in haystack for token in ("maintenance", "backfill", "optimize", "prune", "merge")):
        return "maintain"
    if any(token in haystack for token in ("start", "stop", "restart", "run", "execute", "ausführen", "ausfuehren")):
        return "execute"
    if any(token in haystack for token in ("search", "semantic", "recall", "stichwort", "fts")):
        return "search"
    if any(token in haystack for token in ("graph search", "durchsuch", "suche", "find")):
        return "search"
    if any(token in haystack for token in ("inspect", "details", "metadata", "ports", "labels", "mounts")):
        return "inspect"
    if "logs" in haystack or "log " in haystack:
        return "logs"
    if any(token in haystack for token in ("inventory", "list", "auflisten")):
        return "list"
    if any(token in haystack for token in ("get", "load", "recent", "neighbors", "healthcheck", "stats", "status")):
        return "read"
    return ""


def infer_tool_target_scopes(tool: ToolDescriptor) -> set[str]:
    explicit = {
        str(item).strip().lower()
        for item in (tool.capability_target_scopes or [])
        if str(item).strip()
    }
    if explicit:
        return explicit
    domain = infer_tool_domain(tool)
    family = infer_tool_operation_family(tool)
    if domain == "memory":
        if str(tool.name or "").startswith("workspace_"):
            return {"project_docs"}
        if family in {"write", "update", "delete", "maintain"}:
            return {"assistant_identity"}
        return {"assistant_identity", "tool_capability"}
    if domain == "container_runtime":
        return {"runtime_state"}
    if domain == "time":
        return {"time_reference"}
    if domain == "files":
        return {"project_docs"}
    return {"external_world"}


def infer_tool_role(tool: ToolDescriptor) -> str:
    explicit = str(tool.tool_role or "").strip().lower()
    if explicit:
        return explicit
    name = str(tool.name or "").strip().lower()
    family = infer_tool_operation_family(tool)
    if name == "time_now":
        return "supporting"
    if family in {"delete", "maintain"}:
        return "forbidden_direct"
    return "primary"


def tool_has_side_effects(tool: ToolDescriptor) -> bool:
    risk = str(tool.capability_risk or "").strip().lower()
    if risk and risk not in {"", "read_only"}:
        return True
    return infer_tool_operation_family(tool) in {"write", "update", "delete", "execute", "maintain", "admin"}


def target_scope_from_contract(*, domain: str, intent_kind: str, contract: dict) -> str:
    if domain == "memory":
        return "assistant_identity"
    if domain == "container_runtime":
        return "runtime_state" if str(contract.get("primary_operation") or "").strip() else ""
    if domain == "tools":
        return "tool_capability"
    if domain == "files":
        return "project_docs"
    if domain == "time":
        return "time_reference"
    if intent_kind == "capability_question":
        return "tool_capability"
    return "external_world"


def _tool_haystack(tool: ToolDescriptor) -> str:
    return " ".join(
        [
            str(tool.name or "").strip().lower(),
            str(tool.description or "").strip().lower(),
            str(tool.intent_description or "").strip().lower(),
            " ".join(str(item).strip().lower() for item in tool.intent_keywords or []),
            str(tool.source or "").strip().lower(),
        ]
    )
