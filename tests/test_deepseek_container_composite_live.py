from tests.test_deepseek_piano_taskloop_live import _by_type, _post_chat, live_chat


def test_piano_logzeilen_composite_preserves_list_to_logs(live_chat):
    events = _post_chat(
        conversation_id="piano-logzeilen-composite",
        text="Welche Container laufen und zeige mir die Logzeilen.",
        model=live_chat["model"],
    )
    traces = _by_type(events, "routing_trace")
    assert traces, "Kein routing_trace fuer den Composite-Contract."
    trace = traces[-1]
    assert trace.get("operation") == "list"
    assert trace.get("allowed_operations") == ["list"]
    assert trace.get("allowed_transitions") == ["list->logs"]
    assert _by_type(events, "tool_start"), (
        "Composite-Contract ist sichtbar, aber die initiale list-Operation startet kein Tool."
    )
    assert _by_type(events, "done")[-1].get("done_reason") == "stop"
