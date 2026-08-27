from core.conversation_meta.defaults import build_conversation_meta, build_default_conversation_meta
from core.conversation_meta.policy import build_effective_policy
from utils.memory_defaults import (
    MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY,
    MEMORY_DEFAULT_MAX_MEMORY_HITS_KEY,
    MEMORY_DEFAULT_MODE_KEY,
)
from utils.settings import settings


def test_default_conversation_meta_uses_hardcoded_fallback_without_overrides(monkeypatch):
    """Codex-Entscheidung (P11.0 Checkpoint 4, Settings-Klaerung): die echte,
    versionierte config/settings.json enthaelt bewusst einen persistierten
    Privacy-Override (MEMORY_DEFAULT_MODE=disabled, Commit 9c7ed93) - das ist
    keine zu fixende Korruption, sondern Produktionszustand. Dieser Test
    prueft explizit den HARDCODED Fallback (global_enabled), nicht den
    Override - er muss seine Umgebung daher selbst isolieren, statt sich auf
    eine zufaellige Testreihenfolge zu verlassen. monkeypatch.delitem/delenv
    stellen settings.settings und die Umgebung nach dem Test automatisch
    wieder her - der Singleton-Zustand bleibt fuer andere Tests unveraendert.
    """
    for key in (
        MEMORY_DEFAULT_MODE_KEY,
        MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY,
        MEMORY_DEFAULT_MAX_MEMORY_HITS_KEY,
    ):
        monkeypatch.delitem(settings.settings, key, raising=False)
        monkeypatch.delenv(key, raising=False)

    meta = build_default_conversation_meta("conv-1")

    assert meta.conversation_id == "conv-1"
    assert meta.memory.mode.value == "global_enabled"
    assert meta.memory.do_not_remember is False
    assert meta.status.temporary is False
    assert meta.memory.scopes[0].namespace == "global"


def test_build_conversation_meta_reads_nested_payload():
    meta = build_conversation_meta(
        {
            "conversation_id": "conv-2",
            "title": "Scoped session",
            "status": {"temporary": True, "starred": True},
            "memory": {
                "mode": "conversation_only",
                "do_not_remember": True,
                "scopes": [{"namespace": "project", "key": "trion", "siloed": True}],
            },
            "runtime_scope": {"repo": "example/TRION", "container_id": "abc123"},
        },
        "ignored",
    )

    assert meta.title == "Scoped session"
    assert meta.status.temporary is True
    assert meta.memory.mode.value == "conversation_only"
    assert meta.memory.do_not_remember is True
    assert meta.memory.scopes[0].namespace == "project"
    assert meta.memory.scopes[0].key == "trion"
    assert meta.runtime_scope.repo == "example/TRION"


def test_effective_policy_disables_global_read_and_ltm_write_when_requested():
    meta = build_conversation_meta(
        {
            "conversation_id": "conv-3",
            "status": {"temporary": True},
            "memory": {"mode": "disabled", "do_not_remember": True},
        },
        "conv-3",
    )
    policy = build_effective_policy(meta)

    assert policy.memory_mode.value == "disabled"
    assert policy.allow_global_memory_read is False
    assert policy.allow_long_term_write is False
    assert policy.temporary is True
    assert policy.do_not_remember is True


def test_conversation_only_rewrites_default_global_scope_to_session_scope():
    meta = build_conversation_meta(
        {
            "conversation_id": "conv-4",
            "memory": {"mode": "conversation_only"},
        },
        "conv-4",
    )
    policy = build_effective_policy(meta)

    assert policy.memory_mode.value == "conversation_only"
    assert policy.allow_global_memory_read is False
    assert [scope.namespace for scope in policy.allowed_scopes] == ["session"]
    assert policy.allowed_scopes[0].siloed is True
