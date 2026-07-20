from collections.abc import Mapping
from typing import Any

from core.conversation_meta.contracts import (
    ContextScope,
    ConversationMemoryPolicy,
    ConversationMeta,
    ConversationRoutingState,
    ConversationRuntimeScope,
    ConversationStatus,
    MemoryMode,
)
from utils.memory_defaults import (
    HARDCODED_DEFAULT_DO_NOT_REMEMBER,
    HARDCODED_DEFAULT_MAX_MEMORY_HITS,
    HARDCODED_DEFAULT_MEMORY_MODE,
    MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY,
    MEMORY_DEFAULT_MAX_MEMORY_HITS_KEY,
    MEMORY_DEFAULT_MODE_KEY,
    get_default_do_not_remember_value,
    get_default_max_memory_hits_value,
    get_default_memory_mode_value,
)


def _safe_memory_mode(raw: Any) -> MemoryMode:
    try:
        return MemoryMode(str(raw or "").strip())
    except (ValueError, TypeError):
        return MemoryMode(HARDCODED_DEFAULT_MEMORY_MODE)


def get_default_memory_mode() -> MemoryMode:
    """User-konfigurierbarer globaler Memory-Default, mit Hardcoded-Fallback."""
    return _safe_memory_mode(get_default_memory_mode_value())


def get_default_do_not_remember() -> bool:
    return get_default_do_not_remember_value()


def get_default_max_memory_hits() -> int:
    return get_default_max_memory_hits_value()


def _scopes_for_default_mode(mode: MemoryMode) -> list[ContextScope]:
    if mode == MemoryMode.CONVERSATION_ONLY:
        return [ContextScope(namespace="session", siloed=True)]
    if mode == MemoryMode.DISABLED:
        return []
    return [ContextScope(namespace="global")]


def build_default_conversation_meta(conversation_id: str) -> ConversationMeta:
    conv_id = str(conversation_id or "global").strip() or "global"
    mode = get_default_memory_mode()
    do_not_remember = get_default_do_not_remember()
    return ConversationMeta(
        conversation_id=conv_id,
        memory=ConversationMemoryPolicy(
            mode=mode,
            do_not_remember=do_not_remember,
            scopes=_scopes_for_default_mode(mode),
        ),
    )


def _scope_from_payload(payload: Any) -> ContextScope:
    if not isinstance(payload, Mapping):
        return ContextScope(namespace="global")
    namespace = str(payload.get("namespace") or "global").strip() or "global"
    return ContextScope(
        namespace=namespace,
        key=_optional_text(payload.get("key")),
        sub_scope=_optional_text(payload.get("sub_scope")),
        siloed=bool(payload.get("siloed", False)),
        timestamp=_optional_text(payload.get("timestamp")),
    )


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _memory_mode(raw: Any) -> MemoryMode:
    try:
        return MemoryMode(str(raw or MemoryMode.GLOBAL_ENABLED.value).strip() or MemoryMode.GLOBAL_ENABLED.value)
    except ValueError:
        return MemoryMode.GLOBAL_ENABLED


def build_conversation_meta(payload: Mapping[str, Any] | None, conversation_id: str) -> ConversationMeta:
    default = build_default_conversation_meta(conversation_id)
    if not isinstance(payload, Mapping):
        return default

    status_payload = payload.get("status")
    memory_payload = payload.get("memory")
    runtime_payload = payload.get("runtime_scope")
    routing_payload = payload.get("routing")

    scopes_payload = memory_payload.get("scopes") if isinstance(memory_payload, Mapping) else None
    scopes = [_scope_from_payload(item) for item in scopes_payload] if isinstance(scopes_payload, list) and scopes_payload else list(default.memory.scopes)

    return ConversationMeta(
        conversation_id=str(payload.get("conversation_id") or default.conversation_id).strip() or default.conversation_id,
        title=str(payload.get("title") or "").strip(),
        created_at=_optional_text(payload.get("created_at")),
        updated_at=_optional_text(payload.get("updated_at")),
        status=ConversationStatus(
            archived=bool(status_payload.get("archived", False)) if isinstance(status_payload, Mapping) else False,
            starred=bool(status_payload.get("starred", False)) if isinstance(status_payload, Mapping) else False,
            temporary=bool(status_payload.get("temporary", False)) if isinstance(status_payload, Mapping) else False,
            pinned_at=_optional_text(status_payload.get("pinned_at")) if isinstance(status_payload, Mapping) else None,
        ),
        memory=ConversationMemoryPolicy(
            mode=_memory_mode(memory_payload.get("mode")) if isinstance(memory_payload, Mapping) else default.memory.mode,
            do_not_remember=bool(memory_payload.get("do_not_remember", False)) if isinstance(memory_payload, Mapping) else False,
            scopes=scopes,
        ),
        runtime_scope=ConversationRuntimeScope(
            project_id=_optional_text(runtime_payload.get("project_id")) if isinstance(runtime_payload, Mapping) else None,
            repo=_optional_text(runtime_payload.get("repo")) if isinstance(runtime_payload, Mapping) else None,
            workspace_id=_optional_text(runtime_payload.get("workspace_id")) if isinstance(runtime_payload, Mapping) else None,
            container_id=_optional_text(runtime_payload.get("container_id")) if isinstance(runtime_payload, Mapping) else None,
            runtime_profile=_optional_text(runtime_payload.get("runtime_profile")) if isinstance(runtime_payload, Mapping) else None,
            safety_profile=_optional_text(runtime_payload.get("safety_profile")) if isinstance(runtime_payload, Mapping) else None,
        ),
        routing=ConversationRoutingState(
            current_node_id=_optional_text(routing_payload.get("current_node_id")) if isinstance(routing_payload, Mapping) else None,
            last_message_id=_optional_text(routing_payload.get("last_message_id")) if isinstance(routing_payload, Mapping) else None,
            template_id=_optional_text(routing_payload.get("template_id")) if isinstance(routing_payload, Mapping) else None,
        ),
    )
