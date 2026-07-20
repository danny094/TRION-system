from core.task_loop.run_governor import can_start_tool_call, current_time_ts, run_governor_from_snapshot


def toolcall_governor_error(snapshot: object | None) -> str:
    if snapshot is None:
        return ""
    decision = can_start_tool_call(run_governor_from_snapshot(snapshot), now_ts=current_time_ts())
    return "" if decision.allowed else decision.reason
