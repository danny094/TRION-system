"""P11.0 SP4 Round 3: ausgelagert aus tests/test_orchestrator_stage.py
(Doc 07, Max 200 Zeilen pro Datei). Deckt Home-Context (verifizierte
Container-Capabilities) und Self-Context (Policy-/Home-Scope-basierte
Capability-Liste) ab. Basisrouting bleibt in tests/test_orchestrator_stage.py,
Evidence-/Tool-Metadaten in tests/test_orchestrator_stage_tool_metadata.py.
"""

from core.classifier.contracts import Category
from core.orchestrator.contracts import OrchestratorPackage, ToolDescriptor
from core.pipeline.orchestrator_stage import build_orchestrator_stage

from tests._orchestrator_classifier_helpers import make_classifier_result

_HOME_SCOPE = {
    "is_home": True,
    "manifest_readable": True,
    "home_id": "trion-home",
    "blueprint_id": "trion-home",
    "owner_agent": "trion",
    "runtime_profile": "trion-home",
    "home_root": "/home/trion",
    "allowed_write_roots": ["/home/trion/notes"],
    "verification_sources": ["container_inspect", "home_manifest"],
}


def test_orchestrator_stage_builds_verified_home_context():
    def _orchestrator(*args, **kwargs):
        return OrchestratorPackage(
            available_tools=[
                ToolDescriptor(name="container_list", source="container-commander", capability_domain="container_runtime", capability_operation="list"),
                ToolDescriptor(
                    name="container_inspect",
                    source="container-commander",
                    capability_domain="container_runtime",
                    capability_operation="inspect",
                    capability_required_args=["container_id_or_name"],
                ),
            ],
            selected_tools=[
                ToolDescriptor(
                    name="container_inspect",
                    source="container-commander",
                    capability_domain="container_runtime",
                    capability_operation="inspect",
                    capability_required_args=["container_id_or_name"],
                )
            ],
            context={
                "active_containers": {
                    "active_home": {
                        "container_id": "abc123",
                        "name": "trion-home",
                        "home_scope": _HOME_SCOPE,
                    }
                }
            },
            classifier_result=make_classifier_result(needs_orchestrator=True, category=Category.INFORMATION),
        )

    stage = build_orchestrator_stage(
        "Was ist in meinem Home?",
        make_classifier_result(needs_orchestrator=True, category=Category.INFORMATION),
        conversation_id="conv-home",
        orchestrator_fn=_orchestrator,
        raw_tools=[],
        routing_frame={
            "intent_kind": "current_state_question",
            "domain": "container_runtime",
            "evidence_need": "live_runtime",
            "execution_mode": "retrieve_context",
        },
    )

    home = stage.thinking_context["context"]["home_context"]
    assert home["verified"] is True
    assert home["container_name"] == "trion-home"
    assert "container_inspect" in home["available_capability_classes"]
    assert "file_read" in home["missing_capability_classes"]
    selected = stage.thinking_context["selected_tool_details"][0]
    assert selected["capability_operation"] == "inspect"
    assert selected["capability_required_args"] == ["container_id_or_name"]


def test_orchestrator_stage_builds_self_context_from_policy_and_home_scope():
    def _orchestrator(*args, **kwargs):
        return OrchestratorPackage(
            available_tools=[
                ToolDescriptor(
                    name="container_inspect",
                    source="container-commander",
                    capability_domain="container_runtime",
                    capability_operation="inspect",
                ),
                ToolDescriptor(
                    name="workspace_read",
                    source="memory-mcp",
                    capability_domain="workspace",
                    capability_operation="read",
                ),
            ],
            selected_tools=[],
            context={
                "conversation_policy": {
                    "memory_mode": "conversation_only",
                    "allow_global_memory_read": False,
                    "allow_long_term_write": False,
                },
                "context_scope_filter": {
                    "active": True,
                    "allowed_namespaces": ["session"],
                },
                "runtime": {
                    "now_utc": "2026-05-27T12:34:56+00:00",
                },
                "memory": {
                    "available": True,
                    "items": [{"content": "Notiz"}],
                },
                "active_containers": {
                    "active_home": {
                        "container_id": "abc123",
                        "name": "trion-home",
                        "home_scope": _HOME_SCOPE,
                    }
                },
            },
            classifier_result=make_classifier_result(needs_orchestrator=True, category=Category.INFORMATION),
        )

    stage = build_orchestrator_stage(
        "Was kannst du insgesamt?",
        make_classifier_result(needs_orchestrator=True, category=Category.INFORMATION),
        conversation_id="conv-self",
        orchestrator_fn=_orchestrator,
        raw_tools=[],
        routing_frame={
            "intent_kind": "capability_question",
            "domain": "tools",
            "evidence_need": "self_context",
            "execution_mode": "direct_answer",
        },
    )

    self_context = stage.thinking_context["context"]["self_context"]
    assert self_context["identity"]["name"] == "TRION"
    assert self_context["memory_visibility"]["memory_mode"] == "conversation_only"
    assert self_context["memory_visibility"]["allow_long_term_write"] is False
    assert self_context["current_scope"]["home_scope_verified"] is True
    capability_names = {item["name"]: item for item in self_context["capabilities"]}
    assert capability_names["memory_read"]["status"] == "verified"
    assert capability_names["memory_write"]["status"] == "denied"
    assert capability_names["container_inspect"]["scope"] == "home"
    assert capability_names["workspace_read"]["source"] == "home_context"
