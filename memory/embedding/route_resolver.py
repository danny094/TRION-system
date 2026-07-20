from typing import Optional


def _inline_resolve_target(
    mode: str,
    endpoint_mode: str,
    base_endpoint: str,
    gpu_endpoint: str,
    cpu_endpoint: str,
    fallback_policy: str,
    availability: Optional[dict] = None,
) -> dict:
    """
    Bestimmt effektives Embedding-Target (GPU/CPU/Endpoint).
    Inline-Mirror von utils/embedding_resolver — kein Import aus utils/ möglich
    da memory/ als eigenständiger Container läuft.
    """
    _valid_modes = {"auto", "prefer_gpu", "cpu_only"}
    _valid_policies = {"best_effort", "strict"}
    _valid_ep_modes = {"single", "dual"}

    mode = (mode or "auto").strip().lower()
    endpoint_mode = (endpoint_mode or "single").strip().lower()
    fallback_policy = (fallback_policy or "best_effort").strip().lower()

    if mode not in _valid_modes:
        mode = "auto"
    if endpoint_mode not in _valid_ep_modes:
        endpoint_mode = "single"
    if fallback_policy not in _valid_policies:
        fallback_policy = "best_effort"

    avail = dict(availability) if availability is not None else {"gpu": True, "cpu": True}
    gpu_ok = bool(avail.get("gpu", True))
    cpu_ok = bool(avail.get("cpu", True))
    eff_gpu = (gpu_endpoint or "").strip()
    eff_cpu = (cpu_endpoint or "").strip()

    if mode == "cpu_only":
        if not cpu_ok:
            return {
                "requested_policy": "cpu_only", "requested_target": "cpu",
                "effective_target": None, "fallback_reason": "cpu_unavailable",
                "hard_error": True, "error_code": 503,
                "endpoint": None, "options": {}, "fallback_endpoint": None,
                "fallback_policy": fallback_policy,
                "reason": "cpu_only→cpu_unavailable→hard_error_503", "target": "cpu",
            }
        if endpoint_mode == "dual" and eff_cpu:
            return {
                "requested_policy": "cpu_only", "requested_target": "cpu",
                "effective_target": "cpu", "fallback_reason": None,
                "hard_error": False, "error_code": None,
                "endpoint": eff_cpu, "options": {}, "fallback_endpoint": None,
                "fallback_policy": fallback_policy,
                "reason": "cpu_only/dual→cpu_endpoint", "target": "cpu",
            }
        return {
            "requested_policy": "cpu_only", "requested_target": "cpu",
            "effective_target": "cpu", "fallback_reason": None,
            "hard_error": False, "error_code": None,
            "endpoint": base_endpoint, "options": {"num_gpu": 0},
            "fallback_endpoint": None, "fallback_policy": fallback_policy,
            "reason": "cpu_only/single→base+num_gpu=0", "target": "cpu",
        }

    if gpu_ok:
        if endpoint_mode == "dual" and eff_gpu:
            fb_ep = (eff_cpu or base_endpoint) if fallback_policy == "best_effort" else None
            return {
                "requested_policy": mode, "requested_target": "gpu",
                "effective_target": "gpu", "fallback_reason": None,
                "hard_error": False, "error_code": None,
                "endpoint": eff_gpu, "options": {}, "fallback_endpoint": fb_ep,
                "fallback_policy": fallback_policy,
                "reason": f"{mode}/dual→gpu_endpoint", "target": "gpu",
            }
        return {
            "requested_policy": mode, "requested_target": "gpu",
            "effective_target": "gpu", "fallback_reason": None,
            "hard_error": False, "error_code": None,
            "endpoint": base_endpoint, "options": {}, "fallback_endpoint": None,
            "fallback_policy": fallback_policy,
            "reason": f"{mode}/single→base_endpoint", "target": "gpu",
        }

    if cpu_ok:
        cpu_ep, cpu_opts = (eff_cpu, {}) if (endpoint_mode == "dual" and eff_cpu) else (base_endpoint, {"num_gpu": 0})
        return {
            "requested_policy": mode, "requested_target": "gpu",
            "effective_target": "cpu", "fallback_reason": "gpu_unavailable",
            "hard_error": False, "error_code": None,
            "endpoint": cpu_ep, "options": cpu_opts, "fallback_endpoint": None,
            "fallback_policy": fallback_policy,
            "reason": f"{mode}→gpu_unavailable→cpu_fallback", "target": "cpu",
        }

    return {
        "requested_policy": mode, "requested_target": "gpu",
        "effective_target": None, "fallback_reason": "all_unavailable",
        "hard_error": True, "error_code": 503,
        "endpoint": None, "options": {}, "fallback_endpoint": None,
        "fallback_policy": fallback_policy,
        "reason": f"{mode}→all_unavailable→hard_error_503", "target": "gpu",
    }
