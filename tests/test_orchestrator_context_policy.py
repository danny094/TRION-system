from core.orchestrator.orchestrator import orchestrate

from tests._orchestrator_classifier_helpers import make_classifier_result


def test_orchestrator_includes_context_sources_without_leaking_failures():
    def conversation_meta_source(user_text, conversation_id):
        return {"conversation_id": conversation_id, "memory": {"mode": "global_enabled"}}

    def workspace_source(user_text, conversation_id):
        return {"items": [{"title": user_text}], "conversation": conversation_id}

    def broken_source(user_text, conversation_id):
        raise RuntimeError("source unavailable")

    package = orchestrate(
        "Pruefe offene Aufgaben",
        make_classifier_result(),
        context_sources={
            "conversation_meta": conversation_meta_source,
            "workspace": workspace_source,
            "memory": broken_source,
        },
        conversation_id="conv-2",
    )

    assert package.context["workspace"]["available"] is True
    assert package.context["workspace"]["items"] == [{"title": "Pruefe offene Aufgaben"}]
    assert package.context["workspace"]["conversation"] == "conv-2"
    assert package.context["memory"] == {"available": False, "error": "source unavailable"}


def test_orchestrator_uses_conversation_meta_source_in_shadow_mode():
    def conversation_meta_source(user_text, conversation_id):
        return {
            "conversation_id": conversation_id,
            "status": {"temporary": True},
            "memory": {
                "mode": "conversation_only",
                "do_not_remember": True,
                "scopes": [{"namespace": "project", "key": "trion"}],
            },
        }

    package = orchestrate(
        "Merke dir nur diesen Workspace-Kontext",
        make_classifier_result(),
        context_sources={"conversation_meta": conversation_meta_source},
        conversation_id="conv-meta",
    )

    assert package.context["conversation_meta_source"] == "provided"
    assert package.context["conversation_meta"]["status"]["temporary"] is True
    assert package.context["conversation_policy"]["memory_mode"] == "conversation_only"
    assert package.context["conversation_policy"]["allow_global_memory_read"] is False
    assert package.context["conversation_policy"]["allow_long_term_write"] is False


def test_orchestrator_blocks_global_memory_source_when_policy_disables_it():
    calls = {"memory": 0, "workspace": 0}

    def conversation_meta_source(user_text, conversation_id):
        return {
            "conversation_id": conversation_id,
            "memory": {"mode": "conversation_only"},
        }

    def memory_source(user_text, conversation_id):
        calls["memory"] += 1
        return {"items": [{"kind": "memory"}]}

    def workspace_source(user_text, conversation_id):
        calls["workspace"] += 1
        return {"items": [{"kind": "workspace"}]}

    package = orchestrate(
        "Nutze nur lokalen Kontext",
        make_classifier_result(),
        context_sources={
            "conversation_meta": conversation_meta_source,
            "memory": memory_source,
            "workspace": workspace_source,
        },
        conversation_id="conv-local",
    )

    assert calls == {"memory": 0, "workspace": 0}
    assert package.context["context_scope_filter"]["enabled"] is True
    assert package.context["context_scope_filter"]["active"] is True
    assert package.context["memory"]["skipped"] is True
    assert package.context["memory"]["reason"] == "global_memory_disabled"
    assert package.context["workspace"]["skipped"] is True
    assert package.context["workspace"]["reason"] == "scope_siloed:workspace"


def test_orchestrator_allows_explicit_workspace_scope_and_blocks_memory():
    calls = {"memory": 0, "workspace": 0}

    def conversation_meta_source(user_text, conversation_id):
        return {
            "conversation_id": conversation_id,
            "memory": {
                "mode": "conversation_only",
                "scopes": [{"namespace": "workspace", "key": "ws-1", "siloed": True}],
            },
        }

    def memory_source(user_text, conversation_id):
        calls["memory"] += 1
        return {"items": [{"kind": "memory"}]}

    def workspace_source(user_text, conversation_id):
        calls["workspace"] += 1
        return {"items": [{"kind": "workspace"}]}

    package = orchestrate(
        "Nutze diesen Workspace",
        make_classifier_result(),
        context_sources={
            "conversation_meta": conversation_meta_source,
            "memory": memory_source,
            "workspace": workspace_source,
        },
        conversation_id="conv-workspace",
    )

    assert calls == {"memory": 0, "workspace": 1}
    assert package.context["workspace"]["available"] is True
    assert package.context["workspace"]["scope_namespace"] == "workspace"
    assert package.context["memory"]["skipped"] is True
    assert package.context["memory"]["reason"] == "global_memory_disabled"
