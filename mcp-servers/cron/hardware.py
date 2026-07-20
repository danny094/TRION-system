from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional, Tuple


def _read_host_memory_used_percent() -> Optional[float]:
    """Liest Host-RAM-Auslastung via /proc/meminfo. None wenn nicht verfügbar."""
    try:
        total_kb: Optional[float] = None
        available_kb: Optional[float] = None
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        total_kb = float(parts[1])
                elif line.startswith("MemAvailable:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        available_kb = float(parts[1])
                if total_kb is not None and available_kb is not None:
                    break
        if total_kb is None or total_kb <= 0 or available_kb is None:
            return None
        used_kb = max(0.0, total_kb - max(0.0, available_kb))
        return max(0.0, min(100.0, (used_kb / total_kb) * 100.0))
    except Exception:
        return None


def _read_host_cpu_load_percent() -> Optional[float]:
    """CPU-Auslastung aus 1m-Load-Average normiert auf CPU-Anzahl."""
    try:
        load_1m = float(os.getloadavg()[0])
        cpu_count = max(1, int(os.cpu_count() or 1))
        return max(0.0, (load_1m / float(cpu_count)) * 100.0)
    except Exception:
        return None


def get_hardware_snapshot(probe_cb: Optional[Callable[[], Dict[str, Any]]] = None) -> Dict[str, Any]:
    if callable(probe_cb):
        try:
            snapshot = probe_cb() or {}
        except Exception as exc:
            return {"cpu_percent": None, "memory_percent": None, "probe_error": f"probe_failed:{exc}"}
        cpu_raw = snapshot.get("cpu_percent")
        mem_raw = snapshot.get("memory_percent")
        return {
            "cpu_percent": float(cpu_raw) if isinstance(cpu_raw, (int, float)) else None,
            "memory_percent": float(mem_raw) if isinstance(mem_raw, (int, float)) else None,
            "probe_error": "",
        }
    return {
        "cpu_percent": _read_host_cpu_load_percent(),
        "memory_percent": _read_host_memory_used_percent(),
        "probe_error": "",
    }


def evaluate_hardware_guard(
    snapshot: Dict[str, Any],
    *,
    guard_enabled: bool,
    cpu_max: int,
    mem_max: int,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Gibt (allowed, reason, enriched_snapshot) zurück."""
    result = dict(snapshot)
    if not guard_enabled:
        result["guard_enabled"] = False
        return True, "", result

    cpu = snapshot.get("cpu_percent")
    mem = snapshot.get("memory_percent")
    reason = ""
    if isinstance(cpu, (int, float)) and float(cpu) >= float(cpu_max):
        reason = f"cpu_over_limit:{float(cpu):.1f}>={cpu_max}"
    elif isinstance(mem, (int, float)) and float(mem) >= float(mem_max):
        reason = f"mem_over_limit:{float(mem):.1f}>={mem_max}"

    result.update({"guard_enabled": True, "cpu_limit_percent": cpu_max, "mem_limit_percent": mem_max})
    return reason == "", reason, result
