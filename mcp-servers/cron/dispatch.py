from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict

from .hardware import get_hardware_snapshot, evaluate_hardware_guard
from .state import CronJobStore
from .time_utils import _iso
from utils.logger import log_info, log_warning, log_error


async def dispatch_worker(
    worker_idx: int,
    store: CronJobStore,
    queue: asyncio.Queue,
    submit_cb: Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]],
    stopping_fn: Callable[[], bool],
    *,
    hardware_guard_enabled: bool,
    hardware_cpu_max: int,
    hardware_mem_max: int,
    hardware_probe_cb: Any = None,
) -> None:
    while not stopping_fn():
        try:
            item = await queue.get()
        except asyncio.CancelledError:
            raise

        run_id = str(item.get("run_id", ""))
        async with store.lock:
            store.pending = [x for x in store.pending if str(x.get("run_id")) != run_id]
            running_entry = {**item, "worker": worker_idx, "started_at": _iso()}
            store.running[run_id] = running_entry
            job = store.jobs.get(str(item.get("cron_job_id", "")))
            if job:
                job["last_run_at"] = running_entry["started_at"]
                job["last_status"] = "dispatching"
            store.save()

        try:
            job_id = str(item.get("cron_job_id", ""))
            async with store.lock:
                job = dict(store.jobs.get(job_id) or {})
            if not job:
                raise RuntimeError("cron_job_not_found")

            snapshot = get_hardware_snapshot(hardware_probe_cb)
            allowed, guard_reason, guard_snapshot = evaluate_hardware_guard(
                snapshot, guard_enabled=hardware_guard_enabled,
                cpu_max=hardware_cpu_max, mem_max=hardware_mem_max,
            )
            if not allowed:
                finish = _iso()
                log_warning(
                    f"[AutonomyCron] deferred run_id={run_id} job_id={job_id} reason={guard_reason} "
                    f"cpu={guard_snapshot.get('cpu_percent')} mem={guard_snapshot.get('memory_percent')}"
                )
                async with store.lock:
                    store.running.pop(run_id, None)
                    job_ref = store.jobs.get(job_id)
                    if job_ref:
                        job_ref["last_status"] = "deferred_hardware"
                        job_ref["last_error"] = guard_reason[:300]
                        job_ref["updated_at"] = finish
                    store.append_history({
                        "run_id": run_id, "cron_job_id": job_id, "status": "deferred_hardware",
                        "queued_at": item.get("queued_at"), "started_at": running_entry.get("started_at"),
                        "finished_at": finish, "reason": item.get("reason", "schedule"),
                        "hardware_guard": {"reason": guard_reason, "snapshot": guard_snapshot},
                    })
                    store.save()
                continue

            conversation_id = str(job.get("conversation_id", "")).strip()
            if not conversation_id:
                raise RuntimeError("missing_conversation_id")

            submission = await submit_cb(
                {"objective": str(job.get("objective", "")), "conversation_id": conversation_id,
                 "max_loops": int(job.get("max_loops", 10))},
                {"source": "autonomy_cron", "cron_job_id": job_id,
                 "cron_job_name": str(job.get("name", "")), "cron_run_id": run_id,
                 "reason": str(item.get("reason", "schedule"))},
            )
            submitted_job_id = str(submission.get("job_id", ""))
            finish = _iso()

            async with store.lock:
                store.running.pop(run_id, None)
                job_ref = store.jobs.get(job_id)
                if job_ref:
                    job_ref["last_status"] = "submitted"
                    job_ref["last_job_id"] = submitted_job_id
                    job_ref["last_error"] = ""
                    job_ref["updated_at"] = finish
                    one_shot = str(job_ref.get("schedule_mode", "recurring")).strip().lower() == "one_shot"
                    if one_shot:
                        job_ref["enabled"] = False
                store.append_history({
                    "run_id": run_id, "cron_job_id": job_id, "status": "submitted",
                    "queued_at": item.get("queued_at"), "started_at": running_entry.get("started_at"),
                    "finished_at": finish, "autonomy_job_id": submitted_job_id,
                    "reason": item.get("reason", "schedule"),
                })
                store.save()

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            finish = _iso()
            err = str(exc)
            log_error(f"[AutonomyCron] dispatch failed run_id={run_id}: {err}")
            async with store.lock:
                store.running.pop(run_id, None)
                job_id = str(item.get("cron_job_id", ""))
                job_ref = store.jobs.get(job_id)
                if job_ref:
                    job_ref["last_status"] = "failed"
                    job_ref["last_error"] = err[:300]
                    job_ref["updated_at"] = finish
                    if str(job_ref.get("schedule_mode", "")).lower() == "one_shot":
                        job_ref["enabled"] = False
                store.append_history({
                    "run_id": run_id, "cron_job_id": job_id, "status": "failed",
                    "queued_at": item.get("queued_at"), "started_at": item.get("started_at"),
                    "finished_at": finish, "error": err[:500], "reason": item.get("reason", "schedule"),
                })
                store.save()
        finally:
            queue.task_done()
