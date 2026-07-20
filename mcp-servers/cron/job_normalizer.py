from __future__ import annotations

from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from .cron_parser import validate_cron_expression
from .job_builder import normalize_reference_links, build_default_job_note_md
from .time_utils import _parse_iso_datetime, _utcnow, _iso


def normalize_job_payload(
    payload: Dict[str, Any],
    existing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    prev = existing or {}
    out: Dict[str, Any] = dict(prev)

    if "schedule_mode" in payload or not existing:
        mode_raw = payload.get("schedule_mode") if "schedule_mode" in payload else prev.get("schedule_mode", "recurring")
        schedule_mode = str(mode_raw or "recurring").strip().lower()
        if schedule_mode not in {"recurring", "one_shot"}:
            raise ValueError("schedule_mode must be one of: recurring, one_shot")
        out["schedule_mode"] = schedule_mode
    else:
        schedule_mode = str(prev.get("schedule_mode", "recurring")).strip().lower() or "recurring"

    if "name" in payload or not existing:
        name = str(payload.get("name") if "name" in payload else prev.get("name", "")).strip()
        if not name:
            raise ValueError("name is required")
        out["name"] = name[:120]

    if "objective" in payload or not existing:
        objective = str(payload.get("objective") if "objective" in payload else prev.get("objective", "")).strip()
        if not objective:
            raise ValueError("objective is required")
        out["objective"] = objective[:1000]

    if "conversation_id" in payload or not existing:
        conversation_id = str(
            payload.get("conversation_id") if "conversation_id" in payload else prev.get("conversation_id", "")
        ).strip()
        if not conversation_id:
            raise ValueError("conversation_id is required")
        out["conversation_id"] = conversation_id[:120]

    if schedule_mode == "recurring":
        if "cron" in payload or not existing:
            cron_expr = str(payload.get("cron") if "cron" in payload else prev.get("cron", "")).strip()
            if not cron_expr:
                raise ValueError("cron is required for recurring schedule")
            out["cron"] = str(validate_cron_expression(cron_expr)["normalized"])
        out["run_at"] = ""
    else:
        if "cron" in payload:
            cron_expr = str(payload.get("cron") or "").strip()
            if cron_expr:
                out["cron"] = str(validate_cron_expression(cron_expr)["normalized"])
        elif not existing:
            out["cron"] = "*/15 * * * *"
        run_at_raw = payload.get("run_at") if "run_at" in payload else prev.get("run_at", "")
        run_at_dt = _parse_iso_datetime(str(run_at_raw or ""))
        if run_at_dt is None:
            raise ValueError("run_at is required for one_shot schedule")
        if (existing is None or "run_at" in payload) and run_at_dt <= _utcnow():
            raise ValueError("run_at must be in the future for one_shot schedule")
        out["run_at"] = _iso(run_at_dt)

    if "timezone" in payload or not existing:
        tz_name = str(payload.get("timezone") if "timezone" in payload else prev.get("timezone", "UTC")).strip() or "UTC"
        try:
            ZoneInfo(tz_name)
        except Exception as exc:
            raise ValueError(f"timezone invalid: {tz_name}") from exc
        out["timezone"] = tz_name

    if "max_loops" in payload or not existing:
        raw = payload.get("max_loops") if "max_loops" in payload else prev.get("max_loops", 10)
        try:
            max_loops = int(raw)
        except Exception as exc:
            raise ValueError("max_loops must be an integer") from exc
        if max_loops < 1 or max_loops > 200:
            raise ValueError("max_loops must be between 1 and 200")
        out["max_loops"] = max_loops

    if "created_by" in payload or not existing:
        created_by = str(
            payload.get("created_by") if "created_by" in payload else prev.get("created_by", "user")
        ).strip().lower() or "user"
        if created_by not in {"user", "trion"}:
            raise ValueError("created_by must be one of: user, trion")
        out["created_by"] = created_by

    if "enabled" in payload:
        out["enabled"] = bool(payload.get("enabled"))
    elif not existing:
        out["enabled"] = True

    if "user_approved" in payload:
        out["user_approved"] = bool(payload.get("user_approved"))
    elif not existing:
        out["user_approved"] = False

    if "reference_links" in payload:
        out["reference_links"] = normalize_reference_links(payload.get("reference_links"))

    if "reference_source" in payload:
        out["reference_source"] = str(payload.get("reference_source", "")).strip()[:120]

    if "job_note_md" in payload:
        out["job_note_md"] = str(payload.get("job_note_md") or "").strip()[:6000]
    elif not existing:
        out["job_note_md"] = build_default_job_note_md(out)
    else:
        auto_prev = build_default_job_note_md(prev)
        changed_core = any(k in payload for k in (
            "name", "objective", "schedule_mode", "cron", "run_at",
            "timezone", "conversation_id", "max_loops", "created_by",
        ))
        if changed_core and str(prev.get("job_note_md", "")).strip() in {"", auto_prev}:
            out["job_note_md"] = build_default_job_note_md(out)

    return out
