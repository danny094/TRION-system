"""
Mapping vom UI-nahen Autonomy-Profil auf bestehende Sequential-Runtime-Settings.

Bewusst konservativ: nur Felder mappen, deren technische Bedeutung heute schon
stabil genug ist. Alles andere bleibt vorerst nur Profilzustand.
"""
from typing import Any, Dict


def build_runtime_overrides(profile: Dict[str, Any]) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    overrides.update(_planning_depth_overrides(str(profile.get("planning_depth") or "normal")))
    overrides["SEQUENTIAL_TIMEOUT_S"] = _wait_behavior_timeout(str(profile.get("wait_behavior") or "30sek"))
    overrides.update(_safety_level_overrides(str(profile.get("safety_level") or "standard")))
    overrides.update(_error_behavior_overrides(str(profile.get("error_behavior") or "retry")))
    overrides.update(_mode_overrides(str(profile.get("mode") or "halbautomatisch")))
    overrides["TASK_LOOP_LOOP_DETECTION_ENABLE"] = bool(profile.get("loop_detection_enabled", True))
    overrides["TASK_LOOP_NO_PROGRESS_THRESHOLD"] = _loop_detection_threshold(
        profile.get("loop_detection_sensitivity", 3)
    )
    return overrides


def _planning_depth_overrides(value: str) -> Dict[str, Any]:
    mapping = {
        "schnell": {"TASK_LOOP_MAX_STEPS": 3, "LOOP_ENGINE_MAX_PREDICT": 300, "LOOP_ENGINE_OUTPUT_CHAR_CAP": 1200},
        "normal": {"TASK_LOOP_MAX_STEPS": 10, "LOOP_ENGINE_MAX_PREDICT": 700, "LOOP_ENGINE_OUTPUT_CHAR_CAP": 2400},
        "gründlich": {"TASK_LOOP_MAX_STEPS": 25, "LOOP_ENGINE_MAX_PREDICT": 1400, "LOOP_ENGINE_OUTPUT_CHAR_CAP": 4800},
        "unbegrenzt": {"TASK_LOOP_MAX_STEPS": 100, "LOOP_ENGINE_MAX_PREDICT": 0, "LOOP_ENGINE_OUTPUT_CHAR_CAP": 0},
    }
    return dict(mapping.get(value, mapping["normal"]))


def _wait_behavior_timeout(value: str) -> int:
    mapping = {"sofort": 5, "30sek": 30, "2min": 120, "immer": 300}
    return int(mapping.get(value, 30))


def _loop_detection_threshold(raw: Any) -> int:
    try:
        value = int(raw)
    except Exception:
        value = 3
    return max(2, min(10, value))


def _safety_level_overrides(value: str) -> Dict[str, Any]:
    if value == "erhöht":
        return {
            "QUERY_BUDGET_SKIP_THINKING_ENABLE": False,
            "QUERY_BUDGET_SKIP_THINKING_MIN_CONFIDENCE": 0.98,
            "QUERY_BUDGET_MAX_TOOLS_FACTUAL_LOW": 0,
        }
    return {
        "QUERY_BUDGET_SKIP_THINKING_ENABLE": True,
        "QUERY_BUDGET_SKIP_THINKING_MIN_CONFIDENCE": 0.90,
        "QUERY_BUDGET_MAX_TOOLS_FACTUAL_LOW": 1,
    }


def _error_behavior_overrides(value: str) -> Dict[str, Any]:
    if value == "retry":
        return {
            "TASK_LOOP_MAX_RETRIES_PER_STEP": 1,
            "TASK_LOOP_FAILURE_ESCALATION": "replan",
        }
    if value == "abort":
        return {
            "TASK_LOOP_MAX_RETRIES_PER_STEP": 0,
            "TASK_LOOP_FAILURE_ESCALATION": "abort",
        }
    return {
        "TASK_LOOP_MAX_RETRIES_PER_STEP": 0,
        "TASK_LOOP_FAILURE_ESCALATION": "ask",
    }


def _mode_overrides(value: str) -> Dict[str, Any]:
    if value == "manuell":
        return {
            "LOOP_ENGINE_MIN_TOOLS": 0,
            "QUERY_BUDGET_ENABLE": False,
            "TASK_LOOP_APPROVAL_MODE": "approval_first",
        }
    if value == "autonom":
        return {
            "LOOP_ENGINE_MIN_TOOLS": 1,
            "QUERY_BUDGET_ENABLE": True,
            "TASK_LOOP_APPROVAL_MODE": "permissive",
        }
    return {
        "LOOP_ENGINE_MIN_TOOLS": 1,
        "QUERY_BUDGET_ENABLE": True,
        "TASK_LOOP_APPROVAL_MODE": "risk_based",
    }
