from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from .contracts import CronPolicyError
from .cron_parser import estimate_min_interval_seconds
from .time_utils import _parse_iso_datetime
from .trion_policy import enforce_trion_policy


def enforce_job_policy(
    normalized: Dict[str, Any],
    existing: Optional[Dict[str, Any]],
    *,
    job_id: str = "",
    jobs: Dict[str, Dict],
    max_jobs: int,
    max_jobs_per_conversation: int,
    min_interval_s: int,
    parsed_expr_fn: Callable[[str], Dict[str, Any]],
    count_jobs_for_conversation_fn: Callable[[str, str], int],
    trion_policy_kwargs: Dict[str, Any],
) -> None:
    existing_job = existing or {}
    creating = existing is None
    cur_conv = str(existing_job.get("conversation_id", "")).strip()
    new_conv = str(normalized.get("conversation_id", "")).strip()
    conv_changed = creating or (new_conv != cur_conv)
    computed_min_interval_s: Optional[int] = None

    if creating and len(jobs) >= max_jobs:
        raise CronPolicyError(
            "cron_max_jobs_reached", f"max cron jobs reached ({max_jobs})",
            status_code=409, details={"max_jobs": max_jobs},
        )

    if conv_changed:
        used = count_jobs_for_conversation_fn(new_conv, job_id)
        if used >= max_jobs_per_conversation:
            raise CronPolicyError(
                "cron_conversation_limit_reached",
                f"conversation '{new_conv}' reached cron limit ({max_jobs_per_conversation})",
                status_code=409,
                details={"conversation_id": new_conv, "max_jobs_per_conversation": max_jobs_per_conversation},
            )

    cur_cron = str(existing_job.get("cron", "")).strip()
    new_cron = str(normalized.get("cron", "")).strip()
    schedule_mode = str(
        normalized.get("schedule_mode") if "schedule_mode" in normalized else existing_job.get("schedule_mode", "recurring")
    ).strip().lower() or "recurring"

    if schedule_mode != "one_shot" and (creating or new_cron != cur_cron):
        parsed = parsed_expr_fn(new_cron)
        computed_min_interval_s = estimate_min_interval_seconds(parsed)
        if computed_min_interval_s < min_interval_s:
            raise CronPolicyError(
                "cron_min_interval_violation",
                f"cron interval {computed_min_interval_s}s is below policy minimum {min_interval_s}s",
                status_code=409,
                details={"interval_s": computed_min_interval_s, "min_interval_s": min_interval_s},
            )

    enforce_trion_policy(
        normalized, existing_job,
        creating=creating,
        min_interval_s=computed_min_interval_s,
        schedule_mode=schedule_mode,
        parsed_expr_fn=parsed_expr_fn,
        estimate_interval_fn=estimate_min_interval_seconds,
        **trion_policy_kwargs,
    )


def check_enqueue_policy(
    *,
    cron_job_id: str,
    reason: str,
    now_utc: datetime,
    pending: List[Dict],
    running: Dict[str, Dict],
    jobs: Dict[str, Dict],
    max_pending_runs: int,
    max_pending_runs_per_job: int,
    manual_run_cooldown_s: int,
) -> Tuple[bool, Optional[CronPolicyError]]:
    if len(pending) + len(running) >= max_pending_runs:
        return False, CronPolicyError(
            "cron_queue_capacity_reached", f"cron queue capacity reached ({max_pending_runs})",
            status_code=429, details={"max_pending_runs": max_pending_runs},
        )

    job_runs = (
        sum(1 for x in pending if str(x.get("cron_job_id", "")) == cron_job_id)
        + sum(1 for x in running.values() if str(x.get("cron_job_id", "")) == cron_job_id)
    )
    if job_runs >= max_pending_runs_per_job:
        return False, CronPolicyError(
            "cron_job_backlog_limit_reached", f"cron job backlog reached ({max_pending_runs_per_job})",
            status_code=429, details={"max_pending_runs_per_job": max_pending_runs_per_job},
        )

    if str(reason or "") in {"manual", "tool"} and manual_run_cooldown_s > 0:
        job = jobs.get(cron_job_id) or {}
        last_manual_at = _parse_iso_datetime(str(job.get("last_manual_trigger_at", "")))
        if last_manual_at is not None:
            elapsed = max(0, int((now_utc - last_manual_at).total_seconds()))
            retry_after = manual_run_cooldown_s - elapsed
            if retry_after > 0:
                return False, CronPolicyError(
                    "cron_run_now_cooldown", f"run-now cooldown active ({retry_after}s remaining)",
                    status_code=429, details={"retry_after_s": retry_after},
                )

    return True, None
