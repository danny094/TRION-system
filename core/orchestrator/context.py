from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

from config import get_conversation_scope_filter_enable
from core.conversation_meta.contracts import ContextScope
from core.conversation_meta.defaults import build_conversation_meta, build_default_conversation_meta
from core.conversation_meta.policy import EffectiveConversationPolicy, build_effective_policy
from utils.logger import log_info

ContextSource = Callable[[str, str], Any]
_SOURCE_NAMESPACE_MAP = {
    "memory": "global",
    "global_memory": "global",
    "project": "project",
    "repo": "repo",
    "workspace": "workspace",
    "container": "container",
    "active_containers": "container",
    "runtime": "runtime",
    "user": "user",
    "session": "session",
}


def _read_source(source: ContextSource, user_text: str, conversation_id: str) -> Dict[str, Any]:
    try:
        value = source(user_text, conversation_id)
    except Exception as exc:
        return {"available": False, "error": str(exc)}
    if isinstance(value, dict):
        return {"available": True, **value}
    return {"available": True, "value": value}


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _source_namespace(name: str) -> str | None:
    return _SOURCE_NAMESPACE_MAP.get(str(name).strip().lower())


def _policy_scope_names(policy: EffectiveConversationPolicy) -> set[str]:
    return {scope.namespace for scope in policy.allowed_scopes if scope.namespace}


def _scope_filter_active(policy: EffectiveConversationPolicy) -> bool:
    scopes = policy.allowed_scopes
    if not policy.allow_global_memory_read:
        return True
    if not scopes:
        return False
    if any(scope.siloed for scope in scopes):
        return True
    namespaces = _policy_scope_names(policy)
    return namespaces != {"global"}


def _source_allowed(name: str, policy: EffectiveConversationPolicy) -> tuple[bool, str]:
    namespace = _source_namespace(name)
    if namespace == "global" and not policy.allow_global_memory_read:
        return False, "global_memory_disabled"
    if namespace is None:
        return True, "unclassified_source"

    scopes = policy.allowed_scopes
    if not scopes:
        return True, "no_scope_restriction"

    allowed_namespaces = _policy_scope_names(policy)
    if namespace in allowed_namespaces:
        return True, f"scope_allowed:{namespace}"
    if any(scope.siloed for scope in scopes):
        return False, f"scope_siloed:{namespace}"
    if namespace != "global" and "global" in allowed_namespaces:
        return True, f"global_scope_fallback:{namespace}"
    return False, f"scope_blocked:{namespace}"


def _scope_filter_summary(policy: EffectiveConversationPolicy) -> Dict[str, Any]:
    return {
        "enabled": bool(get_conversation_scope_filter_enable()),
        "active": _scope_filter_active(policy),
        "allowed_scopes": _plain(policy.allowed_scopes),
        "allowed_namespaces": sorted(_policy_scope_names(policy)),
    }


def _load_conversation_meta(
    source: Optional[ContextSource],
    user_text: str,
    conversation_id: str,
) -> tuple[Any, EffectiveConversationPolicy, str]:
    source_name = "default"
    if callable(source):
        try:
            meta = build_conversation_meta(source(user_text, conversation_id), conversation_id)
            source_name = "provided"
        except Exception:
            meta = build_default_conversation_meta(conversation_id)
            source_name = "default_on_error"
    else:
        meta = build_default_conversation_meta(conversation_id)
    policy = build_effective_policy(meta)
    log_info(
        "[Orchestrator] conversation policy "
        f"conversation_id={conversation_id} source={source_name} "
        f"mode={policy.memory_mode.value} temporary={policy.temporary} "
        f"do_not_remember={policy.do_not_remember} "
        f"global_read={policy.allow_global_memory_read} "
        f"long_term_write={policy.allow_long_term_write} "
        f"scope_count={len(policy.allowed_scopes)}"
    )
    return meta, policy, source_name


def build_context(
    user_text: str,
    conversation_id: str = "",
    context_sources: Optional[Dict[str, ContextSource]] = None,
) -> Dict[str, Any]:
    context: Dict[str, Any] = {
        "user_text": str(user_text or ""),
        "conversation_id": str(conversation_id or "global"),
    }
    meta_source = (context_sources or {}).get("conversation_meta")
    meta, policy, source_name = _load_conversation_meta(meta_source, context["user_text"], context["conversation_id"])
    scope_filter_summary = _scope_filter_summary(policy)
    context["conversation_meta"] = _plain(meta)
    context["conversation_policy"] = _plain(policy)
    context["conversation_meta_source"] = source_name
    context["context_scope_filter"] = scope_filter_summary

    for name, source in (context_sources or {}).items():
        if str(name) == "conversation_meta":
            continue
        if scope_filter_summary["enabled"] and scope_filter_summary["active"]:
            allowed, reason = _source_allowed(str(name), policy)
            if not allowed:
                context[str(name)] = {
                    "available": False,
                    "skipped": True,
                    "reason": reason,
                    "namespace": _source_namespace(str(name)),
                }
                continue
        if not callable(source):
            context[str(name)] = {"available": False, "error": "source_not_callable"}
            continue
        source_value = _read_source(source, context["user_text"], context["conversation_id"])
        namespace = _source_namespace(str(name))
        if namespace and source_value.get("available") is True:
            source_value["scope_namespace"] = namespace
        context[str(name)] = source_value
    return context
