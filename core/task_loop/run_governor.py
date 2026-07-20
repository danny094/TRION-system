import time
from dataclasses import dataclass, replace


RUN_GOVERNOR_CANCELLED = "run_governor_cancelled"
RUN_GOVERNOR_MAX_TOTAL_STEPS = "run_governor_max_total_steps"
RUN_GOVERNOR_MAX_TOOL_CALLS = "run_governor_max_tool_calls"
RUN_GOVERNOR_MAX_REPLANS = "run_governor_max_replans"
RUN_GOVERNOR_DEADLINE = "run_governor_deadline"


@dataclass(frozen=True)
class RunGovernorDecision:
    allowed: bool
    reason: str = ""


@dataclass(frozen=True)
class RunGovernorState:
    total_steps: int = 0
    tool_calls: int = 0
    replans: int = 0
    max_total_steps: int | None = None
    max_tool_calls: int | None = None
    max_replans: int | None = None
    deadline_ts: float | None = None
    cancelled: bool = False

    def with_started_step(self) -> "RunGovernorState":
        return replace(self, total_steps=max(0, int(self.total_steps)) + 1)

    def with_started_tool_call(self) -> "RunGovernorState":
        return replace(self, tool_calls=max(0, int(self.tool_calls)) + 1)

    def with_replan(self) -> "RunGovernorState":
        return replace(self, replans=max(0, int(self.replans)) + 1)

    def with_cancelled(self) -> "RunGovernorState":
        return replace(self, cancelled=True)


def can_start_step(state: RunGovernorState, *, now_ts: float | None = None) -> RunGovernorDecision:
    blocked = _common_block(state, now_ts=now_ts)
    if blocked is not None:
        return blocked
    if _limit_reached(state.total_steps, state.max_total_steps):
        return _blocked(RUN_GOVERNOR_MAX_TOTAL_STEPS)
    return RunGovernorDecision(True)


def can_start_tool_call(state: RunGovernorState, *, now_ts: float | None = None) -> RunGovernorDecision:
    blocked = _common_block(state, now_ts=now_ts)
    if blocked is not None:
        return blocked
    if _limit_reached(state.tool_calls, state.max_tool_calls):
        return _blocked(RUN_GOVERNOR_MAX_TOOL_CALLS)
    return RunGovernorDecision(True)


def can_replan(state: RunGovernorState, *, now_ts: float | None = None) -> RunGovernorDecision:
    blocked = _common_block(state, now_ts=now_ts)
    if blocked is not None:
        return blocked
    if _limit_reached(state.replans, state.max_replans):
        return _blocked(RUN_GOVERNOR_MAX_REPLANS)
    return RunGovernorDecision(True)


def run_governor_from_snapshot(snapshot: object) -> RunGovernorState:
    return RunGovernorState(
        total_steps=_non_negative_int(getattr(snapshot, "total_steps", 0)),
        tool_calls=_non_negative_int(getattr(snapshot, "tool_calls", 0)),
        replans=_non_negative_int(getattr(snapshot, "replan_count", 0)),
        max_total_steps=_optional_non_negative_int(getattr(snapshot, "max_total_steps", None)),
        max_tool_calls=_optional_non_negative_int(getattr(snapshot, "max_tool_calls", None)),
        max_replans=_optional_non_negative_int(getattr(snapshot, "max_replans", None)),
        deadline_ts=_optional_float(getattr(snapshot, "deadline_ts", None)),
    )


def replan_governor_from_snapshot(snapshot: object) -> RunGovernorState:
    return run_governor_from_snapshot(snapshot)


def _common_block(state: RunGovernorState, *, now_ts: float | None) -> RunGovernorDecision | None:
    if state.cancelled:
        return _blocked(RUN_GOVERNOR_CANCELLED)
    if state.deadline_ts is not None and now_ts is not None and now_ts >= state.deadline_ts:
        return _blocked(RUN_GOVERNOR_DEADLINE)
    return None


def current_time_ts() -> float:
    return time.time()


def _limit_reached(current: int, limit: int | None) -> bool:
    if limit is None:
        return False
    return _non_negative_int(current) >= _non_negative_int(limit)


def _blocked(reason: str) -> RunGovernorDecision:
    return RunGovernorDecision(False, reason)


def _optional_non_negative_int(value: object) -> int | None:
    if value is None:
        return None
    return _non_negative_int(value)


def _non_negative_int(value: object) -> int:
    return max(0, int(value or 0))


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
