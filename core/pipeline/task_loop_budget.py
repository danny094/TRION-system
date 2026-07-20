"""Sammelt die nicht-patchbaren Task-Loop-Budget-Kwargs aus Config.

Eine Aufgabe: Config-Werte fuer build_task_loop_stage() buendeln, die in
keinem Test ueber `monkeypatch.setattr(runner, ...)` direkt auf dem
core.pipeline.runner-Modul ersetzt werden. `max_steps`, `max_retries_per_step`
und `max_replans` werden bewusst NICHT hier gebuendelt, weil
tests/test_core_pipeline_task_loop.py genau diese drei Namen auf dem
runner-Modul selbst patcht — sie bleiben dort als direkte Imports/Calls.

Reine Verdrahtung, keine eigene Logik, kein LLM-Call.
"""
from __future__ import annotations

from typing import Any, Dict

from config import (
    get_autonomy_approval_required_tools,
    get_sequential_timeout_s,
    get_task_loop_approval_mode,
    get_task_loop_failure_escalation,
    get_task_loop_loop_detection_enable,
    get_task_loop_no_progress_threshold,
)


def collect_task_loop_budget() -> Dict[str, Any]:
    """Liefert die restlichen Budget-/Policy-Kwargs fuer build_task_loop_stage()."""
    return {
        "loop_detection_enabled": get_task_loop_loop_detection_enable(),
        "no_progress_threshold": get_task_loop_no_progress_threshold(),
        "approval_mode": get_task_loop_approval_mode(),
        "failure_escalation": get_task_loop_failure_escalation(),
        "approval_required_tools": get_autonomy_approval_required_tools(),
        "default_timeout_s": float(get_sequential_timeout_s()),
    }
