from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterable

from core.conversation_meta.defaults import get_default_max_memory_hits
from core.self_context.contracts import CapabilityState, SelfContext
from utils.trion_home_contract import (
    capability_class_from_domain_operation,
    capability_description,
)


def build_self_context(
    *,
    conversation_id: str,
    orchestrator_context: Dict[str, Any],
    available_tool_details: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    context = orchestrator_context if isinstance(orchestrator_context, dict) else {}
    policy = context.get("conversation_policy") if isinstance(context.get("conversation_policy"), dict) else {}
    runtime = context.get("runtime") if isinstance(context.get("runtime"), dict) else {}
    memory = context.get("memory") if isinstance(context.get("memory"), dict) else {}
    home = context.get("home_context") if isinstance(context.get("home_context"), dict) else {}
    checked_at = str(runtime.get("now_utc") or "").strip() or None

    capabilities: dict[str, CapabilityState] = {}
    _add_memory_capabilities(capabilities, policy, checked_at)
    _add_tool_capabilities(capabilities, available_tool_details, checked_at)
    _add_home_capabilities(capabilities, home, checked_at)

    self_context = SelfContext(
        identity={
            "name": "TRION",
            "role": "local_first_ai_os_agent",
            "source": "core_identity",
            "status": "verified",
            "confidence": 1.0,
            "checked_at": checked_at,
        },
        current_scope={
            "conversation_id": str(conversation_id or "global"),
            "runtime_profile": str(home.get("runtime_profile") or "").strip(),
            "home_container_name": str(home.get("container_name") or "").strip(),
            "home_scope_verified": home.get("verified") is True,
            "allowed_scope_namespaces": list(context.get("context_scope_filter", {}).get("allowed_namespaces") or []),
            "scope_filter_active": bool(context.get("context_scope_filter", {}).get("active")),
            "source": "conversation_policy+runtime",
            "status": "verified",
            "confidence": 0.95,
            "checked_at": checked_at,
        },
        capabilities=sorted(capabilities.values(), key=lambda item: (item.scope, item.name)),
        memory_visibility={
            "memory_mode": str(policy.get("memory_mode") or "unknown"),
            "conversation_scoped": not bool(policy.get("allow_global_memory_read")),
            "allow_global_memory_read": bool(policy.get("allow_global_memory_read")),
            "allow_long_term_write": bool(policy.get("allow_long_term_write")),
            "raw_memory_visible": False,
            "long_term_memory_mode": "search_only",
            "max_memory_hits": get_default_max_memory_hits(),
            "source": "conversation_policy",
            "status": "verified",
            "confidence": 1.0,
            "checked_at": checked_at,
        },
        uncertainties=_build_uncertainties(home, memory, checked_at),
    )
    return asdict(self_context)


def _add_memory_capabilities(
    target: dict[str, CapabilityState],
    policy: Dict[str, Any],
    checked_at: str | None,
) -> None:
    memory_mode = str(policy.get("memory_mode") or "").strip().lower()
    allow_long_term_write = bool(policy.get("allow_long_term_write"))
    if memory_mode == "disabled":
        target["memory_read"] = CapabilityState(
            name="memory_read",
            description=_describe_capability("memory_read"),
            status="denied",
            source="conversation_policy",
            confidence=1.0,
            checked_at=checked_at,
            scope="agent",
        )
        target["memory_write"] = CapabilityState(
            name="memory_write",
            description=_describe_capability("memory_write"),
            status="denied",
            source="conversation_policy",
            confidence=1.0,
            checked_at=checked_at,
            scope="agent",
        )
        return
    target["memory_read"] = CapabilityState(
        name="memory_read",
        description=_describe_capability("memory_read"),
        status="verified",
        source="conversation_policy",
        confidence=0.95,
        checked_at=checked_at,
        scope="agent",
    )
    target["memory_write"] = CapabilityState(
        name="memory_write",
        description=_describe_capability("memory_write"),
        status="verified" if allow_long_term_write else "denied",
        source="conversation_policy",
        confidence=0.95 if allow_long_term_write else 1.0,
        checked_at=checked_at,
        scope="agent",
    )


def _add_tool_capabilities(
    target: dict[str, CapabilityState],
    tool_details: Iterable[Dict[str, Any]],
    checked_at: str | None,
) -> None:
    backing_counts: dict[str, int] = {}
    discovered: dict[str, str] = {}
    for item in tool_details:
        if not isinstance(item, dict):
            continue
        normalized = capability_class_from_domain_operation(
            item.get("capability_domain"),
            item.get("capability_operation"),
        )
        if normalized is None:
            continue
        name, scope = normalized
        backing_counts[name] = backing_counts.get(name, 0) + 1
        discovered.setdefault(name, scope)

    for name, scope in discovered.items():
        if name in target:
            continue
        target[name] = CapabilityState(
            name=name,
            description=_describe_capability(name),
            status="verified",
            source=f"tool_intent_discovery:{backing_counts[name]}",
            confidence=0.9,
            checked_at=checked_at,
            scope=scope,
        )


def _add_home_capabilities(
    target: dict[str, CapabilityState],
    home: Dict[str, Any],
    checked_at: str | None,
) -> None:
    if home.get("verified") is not True:
        return
    for capability in list(home.get("available_capability_classes") or []):
        name = str(capability or "").strip()
        if not name:
            continue
        target[name] = CapabilityState(
            name=name,
            description=_describe_capability(name),
            status="verified",
            source="home_context",
            confidence=0.98,
            checked_at=checked_at,
            scope="home",
        )


def _build_uncertainties(
    home: Dict[str, Any],
    memory: Dict[str, Any],
    checked_at: str | None,
) -> list[Dict[str, Any]]:
    uncertainties: list[Dict[str, Any]] = []
    if home and home.get("verified") is not True:
        uncertainties.append(
            {
                "subject": "home_scope",
                "status": "unknown",
                "source": "active_containers",
                "message": "Home-Scope ist aktuell nicht verifiziert.",
                "checked_at": checked_at,
            }
        )
    if memory.get("available") is False:
        uncertainties.append(
            {
                "subject": "memory_context",
                "status": "unknown",
                "source": "memory_source",
                "message": str(memory.get("reason") or memory.get("error") or "Memory-Kontext nicht verfuegbar.").strip(),
                "checked_at": checked_at,
            }
        )
    return uncertainties


def _describe_capability(name: str) -> str:
    return capability_description(name)
