from core.routing_frame.gates import (
    should_keep_orchestrator_context,
    should_run_orchestrator_for_frame,
)


def test_gate_keeps_classifier_forced_orchestrator_requests():
    assert should_run_orchestrator_for_frame([{"name": "time_now"}], None) is True


def test_gate_promotes_memory_loop_request_even_without_raw_tools():
    assert should_run_orchestrator_for_frame(
        [],
        {
            "intent_kind": "task_loop_request",
            "domain": "memory",
            "evidence_need": "memory_context",
            "execution_mode": "loop",
        },
    ) is True


def test_gate_does_not_promote_plain_smalltalk_without_evidence_need():
    assert should_run_orchestrator_for_frame(
        [{"name": "memory_graph_search"}],
        {
            "intent_kind": "smalltalk",
            "domain": "general",
            "evidence_need": "none",
            "execution_mode": "direct_answer",
        },
    ) is False


def test_keep_orchestrator_context_for_capability_question_without_selected_tools():
    assert (
        should_keep_orchestrator_context(
            {
                "intent_kind": "capability_question",
                "domain": "tools",
                "evidence_need": "self_context",
                "execution_mode": "direct_answer",
            },
            selected_tool_count=0,
        )
        is True
    )
