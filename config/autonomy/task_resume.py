"""
config.autonomy.task_resume
===========================
Persistenz-Konfig fuer Task-Loop-Resume (WAITING -> approve).
"""
import os

from config.infra.adapter import settings


def get_autonomy_task_resume_store_path() -> str:
    """Dateipfad fuer persistierte WAITING-Tasks."""
    raw = settings.get(
        "AUTONOMY_TASK_RESUME_STORE_PATH",
        os.getenv("AUTONOMY_TASK_RESUME_STORE_PATH", "/tmp/trion/task_resume_store.json"),
    )
    value = str(raw or "").strip()
    return value or "/tmp/trion/task_resume_store.json"


def get_autonomy_task_resume_max_tasks() -> int:
    """Maximale Anzahl gespeicherter Tasks (aelteste werden verworfen)."""
    raw = settings.get(
        "AUTONOMY_TASK_RESUME_MAX_TASKS",
        os.getenv("AUTONOMY_TASK_RESUME_MAX_TASKS", "200"),
    )
    try:
        return max(10, int(str(raw or "200").strip()))
    except Exception:
        return 200
