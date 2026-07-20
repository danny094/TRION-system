from __future__ import annotations

import asyncio
import os
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .cron_parser import validate_cron_expression, next_matching_utc
from .dispatch import dispatch_worker
from .job_crud import CronJobCRUDMixin
from .state import CronJobStore
from .tick import tick_loop
from .time_utils import _iso, _parse_iso_datetime
from utils.logger import log_info


class AutonomyCronScheduler(CronJobCRUDMixin):
    def __init__(
        self,
        state_path: str,
        tick_s: int,
        max_concurrency: int,
        submit_cb: Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]],
        *,
        max_jobs: int = 200,
        max_jobs_per_conversation: int = 30,
        min_interval_s: int = 300,
        max_pending_runs: int = 500,
        max_pending_runs_per_job: int = 2,
        manual_run_cooldown_s: int = 30,
        trion_safe_mode: bool = True,
        trion_min_interval_s: int = 900,
        trion_max_loops: int = 12,
        trion_require_approval_for_risky: bool = True,
        hardware_guard_enabled: bool = True,
        hardware_cpu_max_percent: int = 90,
        hardware_mem_max_percent: int = 92,
        hardware_probe_cb: Optional[Callable[[], Dict[str, Any]]] = None,
    ):
        self._store = CronJobStore(state_path)
        self._tick_s = max(5, int(tick_s))
        self._max_concurrency = max(1, int(max_concurrency))
        self._submit_cb = submit_cb
        self._queue: asyncio.Queue = asyncio.Queue()
        self._tick_task: Optional[asyncio.Task] = None
        self._workers: List[asyncio.Task] = []
        self._stopping = False
        self._hardware_probe_cb = hardware_probe_cb
        self._policy = {
            "max_jobs": max(1, int(max_jobs)),
            "max_jobs_per_conversation": max(1, int(max_jobs_per_conversation)),
            "min_interval_s": max(60, int(min_interval_s)),
            "max_pending_runs": max(1, int(max_pending_runs)),
            "max_pending_runs_per_job": max(1, int(max_pending_runs_per_job)),
            "manual_run_cooldown_s": max(0, int(manual_run_cooldown_s)),
            "trion_safe_mode": bool(trion_safe_mode),
            "trion_min_interval_s": max(60, int(trion_min_interval_s)),
            "trion_max_loops": max(1, int(trion_max_loops)),
            "trion_require_approval_for_risky": bool(trion_require_approval_for_risky),
            "hardware_guard_enabled": bool(hardware_guard_enabled),
            "hardware_cpu_max_percent": max(50, min(99, int(hardware_cpu_max_percent))),
            "hardware_mem_max_percent": max(50, min(99, int(hardware_mem_max_percent))),
        }

    async def start(self) -> None:
        async with self._store.lock:
            self._store.load()
            if self._tick_task and not self._tick_task.done():
                return
            self._stopping = False
            self._tick_task = asyncio.create_task(
                tick_loop(self._store, self._queue, self._tick_s, lambda: self._stopping),
                name="autonomy-cron-tick",
            )
            self._workers = [
                asyncio.create_task(
                    dispatch_worker(
                        i, self._store, self._queue, self._submit_cb, lambda: self._stopping,
                        hardware_guard_enabled=self._policy["hardware_guard_enabled"],
                        hardware_cpu_max=self._policy["hardware_cpu_max_percent"],
                        hardware_mem_max=self._policy["hardware_mem_max_percent"],
                        hardware_probe_cb=self._hardware_probe_cb,
                    ),
                    name=f"autonomy-cron-worker-{i}",
                )
                for i in range(self._max_concurrency)
            ]
        log_info(f"[AutonomyCron] started tick={self._tick_s}s workers={self._max_concurrency}")

    async def stop(self) -> None:
        async with self._store.lock:
            self._stopping = True
            tasks = [t for t in [self._tick_task, *self._workers] if t]
            self._tick_task = None
            self._workers = []
        for task in tasks:
            if task and not task.done():
                task.cancel()
        for task in tasks:
            if task:
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        log_info("[AutonomyCron] stopped")

    def _next_run_iso(self, job: Dict[str, Any]) -> str:
        try:
            if str(job.get("schedule_mode", "recurring")).strip().lower() == "one_shot":
                run_at = _parse_iso_datetime(str(job.get("run_at", "")))
                if run_at is None or str(job.get("last_trigger_key", "")).startswith("one_shot:"):
                    return ""
                return _iso(run_at)
            return next_matching_utc(
                self._store.parsed_expr(str(job.get("cron", ""))), str(job.get("timezone", "UTC"))
            )
        except Exception:
            return ""

    async def list_jobs(self) -> List[Dict[str, Any]]:
        async with self._store.lock:
            out = []
            for job in self._store.jobs.values():
                entry = dict(job)
                entry["next_run_at"] = self._next_run_iso(job) if bool(job.get("enabled", True)) else ""
                entry["runtime_state"] = self._store.runtime_state_for_job(str(job.get("id", "")))
                out.append(entry)
            out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return out

    async def get_job(self, cron_job_id: str) -> Optional[Dict[str, Any]]:
        job_id = str(cron_job_id or "").strip()
        async with self._store.lock:
            job = self._store.jobs.get(job_id)
            if not job:
                return None
            out = dict(job)
            out["next_run_at"] = self._next_run_iso(job) if bool(job.get("enabled", True)) else ""
            out["runtime_state"] = self._store.runtime_state_for_job(job_id)
            return out

    async def get_status(self) -> Dict[str, Any]:
        async with self._store.lock:
            total = len(self._store.jobs)
            enabled = sum(1 for j in self._store.jobs.values() if bool(j.get("enabled", False)))
            return {
                "scheduler": {"running": bool(self._tick_task and not self._tick_task.done()),
                               "tick_s": self._tick_s, "max_concurrency": self._max_concurrency},
                "policy": self._policy,
                "counts": {"jobs_total": total, "jobs_active": enabled, "jobs_paused": total - enabled,
                            "queued_runs": len(self._store.pending), "running_runs": len(self._store.running),
                            "history_runs": len(self._store.history)},
            }

    async def get_queue_snapshot(self) -> Dict[str, Any]:
        async with self._store.lock:
            return {
                "pending": list(self._store.pending),
                "running": list(self._store.running.values()),
                "recent": list(self._store.history[-50:]),
            }


# ── Singleton + server.py-API ─────────────────────────────────────────────────

_scheduler: Optional[AutonomyCronScheduler] = None


def get_scheduler() -> AutonomyCronScheduler:
    global _scheduler
    if _scheduler is None:
        async def _noop_submit(payload: Dict, meta: Dict) -> Dict:
            return {"job_id": ""}
        _scheduler = AutonomyCronScheduler(
            state_path=os.getenv("CRON_STATE_PATH", "/app/data/cron_state.json"),
            tick_s=int(os.getenv("CRON_TICK_S", "60")),
            max_concurrency=int(os.getenv("CRON_MAX_CONCURRENCY", "3")),
            submit_cb=_noop_submit,
        )
    return _scheduler


def validate_cron(*, objective: str, schedule: str) -> Dict[str, Any]:
    try:
        result = validate_cron_expression(schedule)
        return {"valid": True, "normalized": result["normalized"], "objective": str(objective or "").strip()}
    except Exception as exc:
        return {"valid": False, "error": str(exc)}
