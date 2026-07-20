from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Set
from zoneinfo import ZoneInfo

from .contracts import CronParseError
from .time_utils import _utcnow, _iso


@dataclass
class _CronField:
    values: Set[int]
    any: bool


def _parse_int(token: str, lo: int, hi: int, label: str) -> int:
    try:
        value = int(token)
    except Exception as exc:
        raise CronParseError(f"{label}: invalid int '{token}'") from exc
    if value < lo or value > hi:
        raise CronParseError(f"{label}: {value} out of range [{lo},{hi}]")
    return value


def _expand_segment(segment: str, lo: int, hi: int, label: str) -> Set[int]:
    seg = segment.strip()
    if not seg:
        raise CronParseError(f"{label}: empty segment")
    if "/" in seg:
        base, step_raw = seg.split("/", 1)
        step = _parse_int(step_raw, 1, hi - lo + 1, f"{label} step")
    else:
        base, step = seg, 1
    if base == "*" or not base:
        start, end = lo, hi
    elif "-" in base:
        a, b = base.split("-", 1)
        start = _parse_int(a, lo, hi, f"{label} start")
        end = _parse_int(b, lo, hi, f"{label} end")
        if end < start:
            raise CronParseError(f"{label}: range end < start")
    else:
        value = _parse_int(base, lo, hi, label)
        start, end = value, value
    return set(range(start, end + 1, step))


def _parse_field(raw: str, lo: int, hi: int, label: str, normalize_7_to_0: bool = False) -> _CronField:
    token = str(raw or "").strip()
    if token == "*":
        return _CronField(values=set(range(lo, hi + 1)), any=True)
    values: Set[int] = set()
    for part in token.split(","):
        expanded = _expand_segment(part, lo, hi, label)
        if normalize_7_to_0:
            expanded = {0 if x == 7 else x for x in expanded}
        values.update(expanded)
    if not values:
        raise CronParseError(f"{label}: no values parsed")
    return _CronField(values=values, any=False)


def parse_cron_expression(expr: str) -> Dict[str, Any]:
    parts = str(expr or "").strip().split()
    if len(parts) != 5:
        raise CronParseError("cron expression must have 5 fields: min hour dom month dow")
    return {
        "expr": " ".join(parts),
        "minute":       _parse_field(parts[0], 0, 59,  "minute"),
        "hour":         _parse_field(parts[1], 0, 23,  "hour"),
        "day_of_month": _parse_field(parts[2], 1, 31,  "day_of_month"),
        "month":        _parse_field(parts[3], 1, 12,  "month"),
        "day_of_week":  _parse_field(parts[4], 0, 7,   "day_of_week", normalize_7_to_0=True),
    }


def cron_matches(parsed: Dict[str, Any], local_dt: datetime) -> bool:
    if local_dt.minute not in parsed["minute"].values:
        return False
    if local_dt.hour not in parsed["hour"].values:
        return False
    if local_dt.month not in parsed["month"].values:
        return False
    dom = parsed["day_of_month"]
    dow = parsed["day_of_week"]
    dom_match = local_dt.day in dom.values
    dow_match = (local_dt.weekday() + 1) % 7 in dow.values  # 0=sunday
    if dom.any and dow.any:
        return True
    if dom.any:
        return dow_match
    if dow.any:
        return dom_match
    return dom_match or dow_match


def next_matching_utc(
    parsed: Dict[str, Any],
    timezone_name: str,
    from_utc: Optional[datetime] = None,
    max_days: int = 35,
) -> str:
    now_utc = from_utc or _utcnow()
    tz = ZoneInfo(timezone_name)
    local = now_utc.astimezone(tz).replace(second=0, microsecond=0)
    for i in range(1, max_days * 24 * 60 + 1):
        candidate = local + timedelta(minutes=i)
        if cron_matches(parsed, candidate):
            return _iso(candidate.astimezone(timezone.utc))
    return ""


def validate_cron_expression(expr: str) -> Dict[str, Any]:
    parsed = parse_cron_expression(expr)
    return {"valid": True, "normalized": parsed["expr"]}


def estimate_min_interval_seconds(parsed: Dict[str, Any], *, max_days: int = 35, max_hits: int = 40) -> int:
    base = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    prev: Optional[datetime] = None
    min_delta: Optional[int] = None
    hits = 0
    for i in range(max_days * 24 * 60 + 1):
        candidate = base + timedelta(minutes=i)
        if not cron_matches(parsed, candidate):
            continue
        hits += 1
        if prev is not None:
            delta = max(60, int((candidate - prev).total_seconds()))
            min_delta = delta if min_delta is None else min(min_delta, delta)
            if min_delta <= 60:
                break
        prev = candidate
        if hits >= max_hits and min_delta is not None:
            break
    return min_delta if min_delta is not None else (366 * 24 * 60 * 60)
