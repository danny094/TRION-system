from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from .cron_parser import parse_cron_expression
from .time_utils import _iso, _parse_iso_datetime
from utils.logger import log_warning


class CronJobStore:
    """Hält alle Scheduler-State, Persistenz und Expression-Cache."""

    def __init__(self, state_path: str):
        self._state_path = str(state_path or "").strip()
        self.lock = asyncio.Lock()
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.history: List[Dict[str, Any]] = []
        self.pending: List[Dict[str, Any]] = []
        self.running: Dict[str, Dict[str, Any]] = {}
        self._expr_cache: Dict[str, Dict[str, Any]] = {}

    def load(self) -> None:
        self.jobs = {}
        self.history = []
        self.pending = []
        self.running = {}
        if not self._state_path or not os.path.exists(self._state_path):
            return
        try:
            with open(self._state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for job in (data.get("jobs") or []):
                if not isinstance(job, dict):
                    continue
                job_id = str(job.get("id") or "").strip()
                if job_id:
                    self.jobs[job_id] = job
            hist = data.get("history") or []
            if isinstance(hist, list):
                self.history = [x for x in hist if isinstance(x, dict)][-200:]
        except Exception as exc:
            log_warning(f"[AutonomyCron] failed to load state: {exc}")

    def save(self) -> None:
        if not self._state_path:
            return
        parent = os.path.dirname(self._state_path) or "."
        os.makedirs(parent, exist_ok=True)
        data = {
            "version": 1,
            "updated_at": _iso(),
            "jobs": list(self.jobs.values()),
            "history": self.history[-200:],
        }
        tmp = f"{self._state_path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self._state_path)

    def parsed_expr(self, expr: str) -> Dict[str, Any]:
        key = str(expr or "").strip()
        if key not in self._expr_cache:
            self._expr_cache[key] = parse_cron_expression(key)
        return self._expr_cache[key]

    def runtime_state_for_job(self, cron_job_id: str) -> str:
        if any(x.get("cron_job_id") == cron_job_id for x in self.running.values()):
            return "running"
        if any(x.get("cron_job_id") == cron_job_id for x in self.pending):
            return "queued"
        job = self.jobs.get(cron_job_id) or {}
        one_shot = str(job.get("schedule_mode", "recurring")).strip().lower() == "one_shot"
        consumed = str(job.get("last_trigger_key", "")).startswith("one_shot:")
        if one_shot and consumed:
            return "completed"
        return "active" if bool(job.get("enabled", False)) else "paused"

    def count_jobs_for_conversation(self, conversation_id: str, exclude_job_id: str = "") -> int:
        conv = str(conversation_id or "").strip()
        exclude = str(exclude_job_id or "").strip()
        return sum(
            1 for jid, j in self.jobs.items()
            if jid != exclude and str(j.get("conversation_id", "")).strip() == conv
        )

    def count_runs_for_job(self, cron_job_id: str) -> int:
        job_id = str(cron_job_id or "").strip()
        if not job_id:
            return 0
        return (
            sum(1 for x in self.pending if str(x.get("cron_job_id", "")) == job_id)
            + sum(1 for x in self.running.values() if str(x.get("cron_job_id", "")) == job_id)
        )

    def append_history(self, entry: Dict[str, Any]) -> None:
        self.history.append(entry)
        self.history = self.history[-200:]
