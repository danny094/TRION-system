from dataclasses import dataclass

from core.conversation_meta.contracts import ContextScope, ConversationMeta, MemoryMode


@dataclass(frozen=True)
class EffectiveConversationPolicy:
    memory_mode: MemoryMode
    temporary: bool
    do_not_remember: bool
    allow_global_memory_read: bool
    allow_long_term_write: bool
    allowed_scopes: list[ContextScope]


def _default_scopes_for_mode(mode: MemoryMode) -> list[ContextScope]:
    if mode == MemoryMode.CONVERSATION_ONLY:
        return [ContextScope(namespace="session", siloed=True)]
    if mode == MemoryMode.DISABLED:
        return []
    return [ContextScope(namespace="global")]


def build_effective_policy(meta: ConversationMeta) -> EffectiveConversationPolicy:
    mode = meta.memory.mode
    temporary = bool(meta.status.temporary)
    do_not_remember = bool(meta.memory.do_not_remember)

    allow_global_memory_read = mode == MemoryMode.GLOBAL_ENABLED
    allow_long_term_write = mode != MemoryMode.DISABLED and not temporary and not do_not_remember
    scopes = list(meta.memory.scopes)
    if not scopes:
        allowed_scopes = _default_scopes_for_mode(mode)
    elif mode != MemoryMode.GLOBAL_ENABLED and len(scopes) == 1 and scopes[0].namespace == "global":
        allowed_scopes = _default_scopes_for_mode(mode)
    else:
        allowed_scopes = scopes

    return EffectiveConversationPolicy(
        memory_mode=mode,
        temporary=temporary,
        do_not_remember=do_not_remember,
        allow_global_memory_read=allow_global_memory_read,
        allow_long_term_write=allow_long_term_write,
        allowed_scopes=allowed_scopes,
    )
