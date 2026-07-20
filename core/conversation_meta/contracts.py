from dataclasses import dataclass, field
from enum import Enum


class MemoryMode(str, Enum):
    GLOBAL_ENABLED = "global_enabled"
    CONVERSATION_ONLY = "conversation_only"
    DISABLED = "disabled"


@dataclass(frozen=True)
class ContextScope:
    namespace: str
    key: str | None = None
    sub_scope: str | None = None
    siloed: bool = False
    timestamp: str | None = None


@dataclass(frozen=True)
class ConversationStatus:
    archived: bool = False
    starred: bool = False
    temporary: bool = False
    pinned_at: str | None = None


@dataclass(frozen=True)
class ConversationMemoryPolicy:
    mode: MemoryMode = MemoryMode.GLOBAL_ENABLED
    do_not_remember: bool = False
    scopes: list[ContextScope] = field(default_factory=list)


@dataclass(frozen=True)
class ConversationRuntimeScope:
    project_id: str | None = None
    repo: str | None = None
    workspace_id: str | None = None
    container_id: str | None = None
    runtime_profile: str | None = None
    safety_profile: str | None = None


@dataclass(frozen=True)
class ConversationRoutingState:
    current_node_id: str | None = None
    last_message_id: str | None = None
    template_id: str | None = None


@dataclass(frozen=True)
class ConversationMeta:
    conversation_id: str
    title: str = ""
    created_at: str | None = None
    updated_at: str | None = None
    status: ConversationStatus = field(default_factory=ConversationStatus)
    memory: ConversationMemoryPolicy = field(default_factory=ConversationMemoryPolicy)
    runtime_scope: ConversationRuntimeScope = field(default_factory=ConversationRuntimeScope)
    routing: ConversationRoutingState = field(default_factory=ConversationRoutingState)
