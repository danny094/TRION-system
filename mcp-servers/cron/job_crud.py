from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from .job_normalizer import normalize_job_payload
from .job_policy import enforce_job_policy, check_enqueue_policy
from .time_utils import _utcnow, _iso


class CronJobCRUDMixin:
    """CRUD-Operationen für AutonomyCronScheduler. Setzt _store, _policy, _queue voraus."""

    def _enforce_policy(self, normalized: Dict, existing: Optional[Dict], *, job_id: str = "") -> None:
        enforce_job_policy(
            normalized, existing, job_id=job_id,
            jobs=self._store.jobs,
            max_jobs=self._policy["max_jobs"],
            max_jobs_per_conversation=self._policy["max_jobs_per_conversation"],
            min_interval_s=self._policy["min_interval_s"],
            parsed_expr_fn=self._store.parsed_expr,
            count_jobs_for_conversation_fn=self._store.count_jobs_for_conversation,
            trion_policy_kwargs={k: self._policy[k] for k in (
                "trion_safe_mode", "trion_min_interval_s", "trion_max_loops",
                "trion_require_approval_for_risky",
            )},
        )

    async def create_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with self._store.lock:
            now = _iso()
            normalized = normalize_job_payload(payload, existing=None)
            self._enforce_policy(normalized, existing=None)
            job_id = uuid.uuid4().hex[:12]
            job = {
                "id": job_id, **normalized, "created_at": now, "updated_at": now,
                "last_triggered_at": "", "last_run_at": "", "last_status": "never",
                "last_job_id": "", "last_error": "", "last_trigger_key": "", "last_manual_trigger_at": "",
            }
            self._store.jobs[job_id] = job
            self._store.save()
            out = dict(job)
            out["next_run_at"] = self._next_run_iso(job) if bool(job.get("enabled", True)) else ""
            out["runtime_state"] = self._store.runtime_state_for_job(job_id)
            return out

    async def update_job(self, cron_job_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        job_id = str(cron_job_id or "").strip()
        async with self._store.lock:
            current = self._store.jobs.get(job_id)
            if not current:
                return None
            normalized = normalize_job_payload(payload, existing=current)
            self._enforce_policy(normalized, existing=current, job_id=job_id)
            normalized["updated_at"] = _iso()
            self._store.jobs[job_id] = {**current, **normalized}
            self._store.save()
            out = dict(self._store.jobs[job_id])
            out["next_run_at"] = self._next_run_iso(out) if bool(out.get("enabled", True)) else ""
            out["runtime_state"] = self._store.runtime_state_for_job(job_id)
            return out

    async def delete_job(self, cron_job_id: str) -> bool:
        job_id = str(cron_job_id or "").strip()
        async with self._store.lock:
            existed = job_id in self._store.jobs
            self._store.jobs.pop(job_id, None)
            self._store.pending = [x for x in self._store.pending if x.get("cron_job_id") != job_id]
            if existed:
                self._store.save()
            return existed

    async def pause_job(self, cron_job_id: str) -> Optional[Dict[str, Any]]:
        return await self.update_job(cron_job_id, {"enabled": False})

    async def resume_job(self, cron_job_id: str) -> Optional[Dict[str, Any]]:
        return await self.update_job(cron_job_id, {"enabled": True})

    async def run_now(self, cron_job_id: str, reason: str = "manual") -> Optional[Dict[str, Any]]:
        job_id = str(cron_job_id or "").strip()
        async with self._store.lock:
            job = self._store.jobs.get(job_id)
            if not job:
                return None
            now_utc = _utcnow()
            allowed, policy_error = check_enqueue_policy(
                cron_job_id=job_id, reason=str(reason or "manual"), now_utc=now_utc,
                pending=self._store.pending, running=self._store.running, jobs=self._store.jobs,
                max_pending_runs=self._policy["max_pending_runs"],
                max_pending_runs_per_job=self._policy["max_pending_runs_per_job"],
                manual_run_cooldown_s=self._policy["manual_run_cooldown_s"],
            )
            if not allowed and policy_error:
                raise policy_error
            run_id = uuid.uuid4().hex[:12]
            item = {"run_id": run_id, "cron_job_id": job_id, "queued_at": _iso(), "reason": str(reason or "manual")[:40]}
            self._store.pending.append(item)
            await self._queue.put(item)
            self._store.jobs[job_id]["last_triggered_at"] = item["queued_at"]
            one_shot = str(job.get("schedule_mode", "recurring")).lower() == "one_shot"
            if one_shot:
                self._store.jobs[job_id]["last_trigger_key"] = f"one_shot:manual:{item['queued_at']}"
                self._store.jobs[job_id]["enabled"] = False
            else:
                self._store.jobs[job_id]["last_trigger_key"] = ""
            if str(item.get("reason", "")) in {"manual", "tool"}:
                self._store.jobs[job_id]["last_manual_trigger_at"] = item["queued_at"]
            self._store.save()
            out = dict(job)
            out["runtime_state"] = self._store.runtime_state_for_job(job_id)
            out["next_run_at"] = self._next_run_iso(job) if bool(job.get("enabled", True)) else ""
            return {"scheduled": True, "run_id": run_id, "job": out}
