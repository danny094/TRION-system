"""
adapters.admin-api.autonomy_profile_routes
==========================================
GET/POST /api/settings/autonomy/profile

Kleiner Host-Contract fuer den neuen "KI & Verhalten"-Tab.
Dieser Endpoint spricht bewusst die UI-Sprache und entkoppelt
sie von Low-Level-Runtime-Keys.
"""
import importlib.util
import os
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

try:
    from autonomy_profile_mapping import build_runtime_overrides
except ModuleNotFoundError:
    _MAPPING_PATH = Path(__file__).resolve().with_name("autonomy_profile_mapping.py")
    _SPEC = importlib.util.spec_from_file_location("trion_autonomy_profile_mapping", _MAPPING_PATH)
    if _SPEC is None or _SPEC.loader is None:
        raise
    _MODULE = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(_MODULE)
    build_runtime_overrides = _MODULE.build_runtime_overrides
from utils.settings import settings

router = APIRouter(tags=["settings"])

Mode = Literal["manuell", "halbautomatisch", "autonom"]
PlanningDepth = Literal["schnell", "normal", "gründlich", "unbegrenzt"]
WaitBehavior = Literal["sofort", "30sek", "2min", "immer"]
SafetyLevel = Literal["standard", "erhöht"]
ErrorBehavior = Literal["retry", "ask", "abort"]
LoopSensitivity = Literal[2, 3, 5, 10]

_PROFILE_SPECS: Dict[str, Dict[str, Any]] = {
    "AUTONOMY_PROFILE_MODE": {"type": "enum", "default": "halbautomatisch", "choices": {"manuell", "halbautomatisch", "autonom"}},
    "AUTONOMY_PROFILE_PLANNING_DEPTH": {"type": "enum", "default": "normal", "choices": {"schnell", "normal", "gründlich", "unbegrenzt"}},
    "AUTONOMY_PROFILE_WAIT_BEHAVIOR": {"type": "enum", "default": "30sek", "choices": {"sofort", "30sek", "2min", "immer"}},
    "AUTONOMY_PROFILE_SAFETY_LEVEL": {"type": "enum", "default": "standard", "choices": {"standard", "erhöht"}},
    "AUTONOMY_PROFILE_ERROR_BEHAVIOR": {"type": "enum", "default": "retry", "choices": {"retry", "ask", "abort"}},
    "AUTONOMY_PROFILE_LOOP_DETECTION_ENABLED": {"type": "bool", "default": True},
    "AUTONOMY_PROFILE_LOOP_DETECTION_SENSITIVITY": {"type": "int", "default": 3, "choices": {2, 3, 5, 10}},
}

_FIELD_TO_KEY = {
    "mode": "AUTONOMY_PROFILE_MODE",
    "planning_depth": "AUTONOMY_PROFILE_PLANNING_DEPTH",
    "wait_behavior": "AUTONOMY_PROFILE_WAIT_BEHAVIOR",
    "safety_level": "AUTONOMY_PROFILE_SAFETY_LEVEL",
    "error_behavior": "AUTONOMY_PROFILE_ERROR_BEHAVIOR",
    "loop_detection_enabled": "AUTONOMY_PROFILE_LOOP_DETECTION_ENABLED",
    "loop_detection_sensitivity": "AUTONOMY_PROFILE_LOOP_DETECTION_SENSITIVITY",
}

_KEY_TO_FIELD = {value: key for key, value in _FIELD_TO_KEY.items()}


class AutonomyProfile(BaseModel):
    mode: Mode
    planning_depth: PlanningDepth
    wait_behavior: WaitBehavior
    safety_level: SafetyLevel
    error_behavior: ErrorBehavior
    loop_detection_enabled: bool
    loop_detection_sensitivity: LoopSensitivity


class AutonomyProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Optional[Mode] = None
    planning_depth: Optional[PlanningDepth] = None
    wait_behavior: Optional[WaitBehavior] = None
    safety_level: Optional[SafetyLevel] = None
    error_behavior: Optional[ErrorBehavior] = None
    loop_detection_enabled: Optional[bool] = None
    loop_detection_sensitivity: Optional[LoopSensitivity] = None


@router.get("/api/settings/autonomy/profile")
async def get_autonomy_profile():
    profile = _effective_profile()
    return {
        "profile": profile,
        "mapped_runtime": build_runtime_overrides(profile),
        "sources": _effective_sources(),
        "defaults": _default_profile(),
        "restart_required": False,
    }


@router.post("/api/settings/autonomy/profile")
async def update_autonomy_profile(update: AutonomyProfileUpdate):
    payload = update.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=422, detail="No valid fields provided")

    saved: Dict[str, Any] = {}
    for field, value in payload.items():
        key = _FIELD_TO_KEY[field]
        settings.set(key, value)
        saved[field] = value

    profile = _effective_profile()
    mapped_runtime = build_runtime_overrides(profile)
    for key, value in mapped_runtime.items():
        settings.set(key, value)

    return {
        "success": True,
        "saved": saved,
        "profile": profile,
        "mapped_runtime": mapped_runtime,
    }


def _default_profile() -> Dict[str, Any]:
    return {
        _KEY_TO_FIELD[key]: spec["default"]
        for key, spec in _PROFILE_SPECS.items()
    }


def _effective_profile() -> Dict[str, Any]:
    return {
        _KEY_TO_FIELD[key]: _parse_value(key, spec, _raw_profile_value(key, spec))
        for key, spec in _PROFILE_SPECS.items()
    }


def _effective_sources() -> Dict[str, str]:
    return {
        _KEY_TO_FIELD[key]: _source_for(key)
        for key in _PROFILE_SPECS
    }


def _source_for(key: str) -> str:
    if key in settings.settings:
        return "override"
    if os.getenv(key, "").strip():
        return "env"
    return "default"


def _raw_profile_value(key: str, spec: Dict[str, Any]) -> Any:
    if key in settings.settings:
        return settings.get(key, spec["default"])
    env_value = os.getenv(key, "")
    if env_value.strip():
        return env_value
    return spec["default"]


def _parse_value(key: str, spec: Dict[str, Any], raw: Any) -> Any:
    value_type = str(spec.get("type", "str"))
    default = spec.get("default")
    choices = spec.get("choices", set())

    if value_type == "bool":
        return bool(raw) if isinstance(raw, bool) else str(raw).strip().lower() == "true"
    if value_type == "int":
        try:
            value = int(raw)
        except Exception:
            value = int(default)
        return value if value in choices else default
    if value_type == "enum":
        value = str(raw or "").strip()
        return value if value in choices else default
    return raw if raw is not None else default
