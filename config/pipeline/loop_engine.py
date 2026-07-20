"""
config.pipeline.loop_engine
============================
Loop-Engine Schwellenwerte — wann und wie läuft der Task-Loop.

Der LoopEngine wird aktiviert wenn eine Anfrage eine hohe sequenzielle
Komplexität hat und mindestens N Tools vorschlägt. Er hat eigene
Output-Caps und Token-Budgets unabhängig vom normalen Output-Layer.
"""
import os

from config.infra.adapter import settings


def get_loop_engine_trigger_complexity() -> int:
    """
    Minimale sequenzielle Komplexität um den LoopEngine zu aktivieren.
    Skala 1–10, Default 8.
    """
    val = int(settings.get(
        "LOOP_ENGINE_TRIGGER_COMPLEXITY",
        os.getenv("LOOP_ENGINE_TRIGGER_COMPLEXITY", "8"),
    ))
    return max(1, min(10, val))


def get_loop_engine_min_tools() -> int:
    """Minimale Anzahl vorgeschlagener Tools bevor der LoopEngine starten darf."""
    val = int(settings.get(
        "LOOP_ENGINE_MIN_TOOLS",
        os.getenv("LOOP_ENGINE_MIN_TOOLS", "1"),
    ))
    return max(0, min(10, val))


def get_loop_engine_output_char_cap() -> int:
    """Hard-Output-Char-Cap für LoopEngine-Antworten (0 deaktiviert)."""
    val = int(settings.get(
        "LOOP_ENGINE_OUTPUT_CHAR_CAP",
        os.getenv("LOOP_ENGINE_OUTPUT_CHAR_CAP", "2400"),
    ))
    return max(0, min(200000, val))


def get_loop_engine_max_predict() -> int:
    """Max. Token-Prediction-Budget pro LoopEngine-Modell-Runde (0 deaktiviert)."""
    val = int(settings.get(
        "LOOP_ENGINE_MAX_PREDICT",
        os.getenv("LOOP_ENGINE_MAX_PREDICT", "700"),
    ))
    return max(0, min(8192, val))


def get_task_loop_max_steps() -> int:
    """Maximale Anzahl Task-Loop-Schritte pro Lauf."""
    val = int(settings.get(
        "TASK_LOOP_MAX_STEPS",
        os.getenv("TASK_LOOP_MAX_STEPS", "10"),
    ))
    return max(1, min(100, val))


def get_task_loop_max_retries_per_step() -> int:
    """Maximale Wiederholungen pro PlanStep im Task Loop."""
    val = int(settings.get(
        "TASK_LOOP_MAX_RETRIES_PER_STEP",
        os.getenv("TASK_LOOP_MAX_RETRIES_PER_STEP", "1"),
    ))
    return max(0, min(10, val))


def get_task_loop_max_replans() -> int:
    """Maximale Anzahl echter Replan-Versuche pro Task-Loop-Lauf (0 = kein hartes Limit)."""
    val = int(settings.get(
        "TASK_LOOP_MAX_REPLANS",
        os.getenv("TASK_LOOP_MAX_REPLANS", "0"),
    ))
    return max(0, min(1000, val))


def get_task_loop_loop_detection_enable() -> bool:
    """No-progress/loop detection im Task-Loop aktivieren."""
    return str(settings.get(
        "TASK_LOOP_LOOP_DETECTION_ENABLE",
        os.getenv("TASK_LOOP_LOOP_DETECTION_ENABLE", "true"),
    )).strip().lower() == "true"


def get_task_loop_no_progress_threshold() -> int:
    """Nach wie vielen identischen Resultat-Signaturen der Task-Loop blockt."""
    val = int(settings.get(
        "TASK_LOOP_NO_PROGRESS_THRESHOLD",
        os.getenv("TASK_LOOP_NO_PROGRESS_THRESHOLD", "3"),
    ))
    return max(2, min(10, val))


def get_task_loop_approval_mode() -> str:
    """Approval-Gate-Profil fuer Tool-Schritte im Task-Loop."""
    raw = str(settings.get(
        "TASK_LOOP_APPROVAL_MODE",
        os.getenv("TASK_LOOP_APPROVAL_MODE", "risk_based"),
    )).strip().lower()
    return raw if raw in {"approval_first", "risk_based", "permissive"} else "risk_based"


def get_task_loop_failure_escalation() -> str:
    """Bevorzugte Eskalationsrichtung nach erschoepftem Retry-Budget."""
    raw = str(settings.get(
        "TASK_LOOP_FAILURE_ESCALATION",
        os.getenv("TASK_LOOP_FAILURE_ESCALATION", "replan"),
    )).strip().lower()
    return raw if raw in {"replan", "ask", "abort"} else "replan"
