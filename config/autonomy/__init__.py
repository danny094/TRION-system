"""
config.autonomy
===============
Autonomie-Cron-System — zeitgesteuerte autonome Aufgaben.

Module:
  scheduler      → Grundbetrieb: State-Pfad, Tick, Kapazitätslimits
  trion_policy   → TRION-Safe-Mode: strengere Policy für TRION-erstellte Jobs
  hardware_guard → Hardware-Preflight: CPU/RAM-Check vor jedem Dispatch
  tool_policy    → Tool-Allowlist/Blocklist/Approval für autonome Ausführung

Re-Exports für bequemen Zugriff via `from config.autonomy import ...`:
"""
from config.autonomy.scheduler import (
    get_autonomy_cron_state_path,
    get_autonomy_cron_tick_s,
    get_autonomy_cron_max_concurrency,
    get_autonomy_cron_max_jobs,
    get_autonomy_cron_max_jobs_per_conversation,
    get_autonomy_cron_min_interval_s,
    get_autonomy_cron_max_pending_runs,
    get_autonomy_cron_max_pending_runs_per_job,
    get_autonomy_cron_manual_run_cooldown_s,
)

from config.autonomy.trion_policy import (
    get_autonomy_cron_trion_safe_mode,
    get_autonomy_cron_trion_min_interval_s,
    get_autonomy_cron_trion_max_loops,
    get_autonomy_cron_trion_require_approval_for_risky,
)

from config.autonomy.hardware_guard import (
    get_autonomy_cron_hardware_guard_enabled,
    get_autonomy_cron_hardware_cpu_max_percent,
    get_autonomy_cron_hardware_mem_max_percent,
)

from config.autonomy.tool_policy import (
    get_autonomy_tool_allowlist,
    get_autonomy_tool_blocklist,
    get_autonomy_approval_required_tools,
)
from config.autonomy.task_resume import (
    get_autonomy_task_resume_store_path,
    get_autonomy_task_resume_max_tasks,
)

__all__ = [
    # scheduler
    "get_autonomy_cron_state_path", "get_autonomy_cron_tick_s",
    "get_autonomy_cron_max_concurrency", "get_autonomy_cron_max_jobs",
    "get_autonomy_cron_max_jobs_per_conversation", "get_autonomy_cron_min_interval_s",
    "get_autonomy_cron_max_pending_runs", "get_autonomy_cron_max_pending_runs_per_job",
    "get_autonomy_cron_manual_run_cooldown_s",
    # trion_policy
    "get_autonomy_cron_trion_safe_mode", "get_autonomy_cron_trion_min_interval_s",
    "get_autonomy_cron_trion_max_loops", "get_autonomy_cron_trion_require_approval_for_risky",
    # hardware_guard
    "get_autonomy_cron_hardware_guard_enabled", "get_autonomy_cron_hardware_cpu_max_percent",
    "get_autonomy_cron_hardware_mem_max_percent",
    # tool_policy
    "get_autonomy_tool_allowlist", "get_autonomy_tool_blocklist",
    "get_autonomy_approval_required_tools",
    # task_resume
    "get_autonomy_task_resume_store_path", "get_autonomy_task_resume_max_tasks",
]
