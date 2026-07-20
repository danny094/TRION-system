from core.output.grounding_state import clear_grounding_state, get_recent_grounding_state, remember_grounding_state


def setup_function() -> None:
    clear_grounding_state()


def teardown_function() -> None:
    clear_grounding_state()


def test_grounding_state_roundtrip_returns_fresh_snapshot():
    remember_grounding_state(
        conversation_id="conv-1",
        history_len=4,
        grounded_results=[{"tool_name": "time_now", "facts": {"time": "13:58:28"}}],
        now_ts=100.0,
    )

    snapshot = get_recent_grounding_state(
        conversation_id="conv-1",
        history_len=4,
        ttl_s=1200,
        ttl_turns=3,
        now_ts=110.0,
    )

    assert snapshot is not None
    assert snapshot["age_s"] == 10.0
    assert snapshot["age_turns"] == 0
    assert snapshot["grounded_results"][0]["tool_name"] == "time_now"


def test_grounding_state_expires_by_time():
    remember_grounding_state(
        conversation_id="conv-1",
        history_len=4,
        grounded_results=[{"tool_name": "time_now", "facts": {"time": "13:58:28"}}],
        now_ts=100.0,
    )

    snapshot = get_recent_grounding_state(
        conversation_id="conv-1",
        history_len=4,
        ttl_s=30,
        ttl_turns=3,
        now_ts=131.0,
    )

    assert snapshot is None


def test_grounding_state_expires_by_turn_distance():
    remember_grounding_state(
        conversation_id="conv-1",
        history_len=2,
        grounded_results=[{"tool_name": "time_now", "facts": {"time": "13:58:28"}}],
        now_ts=100.0,
    )

    snapshot = get_recent_grounding_state(
        conversation_id="conv-1",
        history_len=6,
        ttl_s=1200,
        ttl_turns=3,
        now_ts=110.0,
    )

    assert snapshot is None
