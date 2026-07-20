from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .contracts import (
    CronPolicyError,
    _TRION_OBJECTIVE_ALLOWED_HINTS,
    _TRION_OBJECTIVE_HARD_BLOCK_HINTS,
    _TRION_OBJECTIVE_RISKY_HINTS,
    _TRION_RISKY_CONTEXT_APPROVED,
)
from .job_builder import collect_keyword_hits


def enforce_trion_policy(
    normalized: Dict[str, Any],
    existing_job: Dict[str, Any],
    *,
    creating: bool,
    min_interval_s: Optional[int],
    schedule_mode: str,
    trion_safe_mode: bool,
    trion_max_loops: int,
    trion_min_interval_s: int,
    trion_require_approval_for_risky: bool,
    parsed_expr_fn: Callable[[str], Dict[str, Any]],
    estimate_interval_fn: Callable[[Dict[str, Any]], int],
) -> None:
    actor = str(
        normalized.get("created_by") if "created_by" in normalized else existing_job.get("created_by", "user")
    ).strip().lower()
    if actor != "trion" or not trion_safe_mode:
        return

    objective = str(
        normalized.get("objective") if "objective" in normalized else existing_job.get("objective", "")
    ).strip()
    if not objective:
        raise CronPolicyError("cron_trion_objective_required", "trion cron objective is required", status_code=400)

    hard_hits = collect_keyword_hits(objective, _TRION_OBJECTIVE_HARD_BLOCK_HINTS)
    if hard_hits:
        raise CronPolicyError(
            "cron_trion_objective_forbidden", "trion objective contains forbidden action pattern",
            status_code=403, details={"forbidden_keywords": hard_hits},
        )

    allow_hits = collect_keyword_hits(objective, _TRION_OBJECTIVE_ALLOWED_HINTS)
    if not allow_hits:
        raise CronPolicyError(
            "cron_trion_objective_not_allowed", "trion objective does not match allowed automation categories",
            status_code=409, details={"required_any_of": list(_TRION_OBJECTIVE_ALLOWED_HINTS)},
        )

    max_loops = int(
        normalized.get("max_loops") if "max_loops" in normalized else existing_job.get("max_loops", 10)
    )
    if max_loops > trion_max_loops:
        raise CronPolicyError(
            "cron_trion_max_loops_violation",
            f"trion max_loops {max_loops} exceeds policy limit {trion_max_loops}",
            status_code=409, details={"max_loops": max_loops, "trion_max_loops": trion_max_loops},
        )

    if schedule_mode != "one_shot":
        interval_s = min_interval_s
        if interval_s is None:
            cron_expr = str(
                normalized.get("cron") if "cron" in normalized else existing_job.get("cron", "")
            ).strip()
            if cron_expr:
                interval_s = estimate_interval_fn(parsed_expr_fn(cron_expr))
        if interval_s is not None and interval_s < trion_min_interval_s:
            raise CronPolicyError(
                "cron_trion_min_interval_violation",
                f"trion cron interval {interval_s}s is below trion minimum {trion_min_interval_s}s",
                status_code=409, details={"interval_s": interval_s, "trion_min_interval_s": trion_min_interval_s},
            )

    if not trion_require_approval_for_risky:
        return

    risky_hits = collect_keyword_hits(objective, _TRION_OBJECTIVE_RISKY_HINTS)
    approved = bool(
        normalized.get("user_approved") if "user_approved" in normalized else existing_job.get("user_approved", False)
    )
    if risky_hits and not approved:
        allow_set = set(collect_keyword_hits(objective, _TRION_OBJECTIVE_ALLOWED_HINTS))
        unapproved = [
            kw for kw in risky_hits
            if not (kw in _TRION_RISKY_CONTEXT_APPROVED and _TRION_RISKY_CONTEXT_APPROVED[kw] & allow_set)
        ]
        if unapproved:
            raise CronPolicyError(
                "cron_trion_approval_required", "trion objective requires explicit user approval",
                status_code=409, details={"risk_keywords": unapproved, "requires": "user_approved=true"},
            )
