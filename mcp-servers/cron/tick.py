from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

from zoneinfo import ZoneInfo

from .cron_parser import cron_matches
from .job_policy import check_enqueue_policy
from .state import CronJobStore
from .time_utils import _utcnow, _iso, _parse_iso_datetime
from utils.logger import log_info, log_warning


async def tick_loop(
    store: CronJobStore,
    queue: asyncio.Queue,
    tick_s: int,
    stopping_fn: Callable[[], bool],
) -> None:
    while not stopping_fn():
        try:
            await tick_once(store, queue)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_warning(f"[AutonomyCron] tick error: {exc}")
        await asyncio.sleep(tick_s)


async def tick_once(store: CronJobStore, queue: asyncio.Queue) -> None:
    now_utc = _utcnow()
    changed = False
    queued = 0

    async with store.lock:
        for job_id, job in store.jobs.items():
            if not bool(job.get("enabled", True)):
                continue

            one_shot = str(job.get("schedule_mode", "recurring")).strip().lower() == "one_shot"
            consumed = str(job.get("last_trigger_key", "")).startswith("one_shot:")

            if one_shot:
                if consumed:
                    continue
                run_at = _parse_iso_datetime(str(job.get("run_at", "")))
                if run_at is None:
                    job["last_status"] = "error"
                    job["last_error"] = "one_shot_run_at_invalid"
                    changed = True
                    continue
                if now_utc < run_at:
                    continue
                allowed, policy_error = check_enqueue_policy(
                    cron_job_id=job_id, reason="schedule_one_shot", now_utc=now_utc,
                    pending=store.pending, running=store.running, jobs=store.jobs,
                    max_pending_runs=500, max_pending_runs_per_job=2, manual_run_cooldown_s=30,
                )
                if not allowed:
                    if policy_error:
                        job["last_status"] = "throttled"
                        job["last_error"] = policy_error.error_code
                        job["updated_at"] = _iso()
                        changed = True
                    continue
                run_id = uuid.uuid4().hex[:12]
                item = {"run_id": run_id, "cron_job_id": job_id, "queued_at": _iso(), "reason": "schedule_one_shot"}
                store.pending.append(item)
                await queue.put(item)
                job["last_triggered_at"] = item["queued_at"]
                job["last_trigger_key"] = f"one_shot:{str(job.get('run_at', ''))}"
                job["enabled"] = False
                changed = True
                queued += 1
                continue

            cron_expr = str(job.get("cron", ""))
            tz_name = str(job.get("timezone", "UTC"))
            try:
                parsed = store.parsed_expr(cron_expr)
                local = now_utc.astimezone(ZoneInfo(tz_name)).replace(second=0, microsecond=0)
            except Exception as exc:
                job["last_status"] = "error"
                job["last_error"] = f"cron_parse_error:{exc}"
                changed = True
                continue

            minute_key = local.strftime("%Y-%m-%dT%H:%M")
            if not cron_matches(parsed, local):
                continue
            if str(job.get("last_trigger_key", "")) == minute_key:
                continue

            allowed, policy_error = check_enqueue_policy(
                cron_job_id=job_id, reason="schedule", now_utc=now_utc,
                pending=store.pending, running=store.running, jobs=store.jobs,
                max_pending_runs=500, max_pending_runs_per_job=2, manual_run_cooldown_s=30,
            )
            if not allowed:
                if policy_error:
                    job["last_status"] = "throttled"
                    job["last_error"] = policy_error.error_code
                    job["updated_at"] = _iso()
                    changed = True
                continue

            run_id = uuid.uuid4().hex[:12]
            item = {"run_id": run_id, "cron_job_id": job_id, "queued_at": _iso(), "reason": "schedule"}
            store.pending.append(item)
            await queue.put(item)
            job["last_triggered_at"] = item["queued_at"]
            job["last_trigger_key"] = minute_key
            changed = True
            queued += 1

        if changed:
            store.save()

    if queued:
        log_info(f"[AutonomyCron] queued scheduled runs: {queued}")
