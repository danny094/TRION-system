import os
from typing import Any, Dict, List, Optional

from commander_runtime_models import NetworkMode

APPROVAL_REQUIRE_BRIDGE = str(os.environ.get("APPROVAL_REQUIRE_BRIDGE", "1")).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DANGEROUS_CAPABILITIES = frozenset(
    {"SYS_ADMIN", "SYS_MODULE", "NET_ADMIN", "SYS_PTRACE", "DAC_READ_SEARCH", "DAC_OVERRIDE"}
)
DANGEROUS_SECURITY_OPTS = frozenset({"seccomp=unconfined"})


def check_needs_approval(network_mode: NetworkMode) -> Optional[str]:
    if network_mode == NetworkMode.FULL:
        return "Container requests internet access (network: full)"
    if network_mode == NetworkMode.BRIDGE and APPROVAL_REQUIRE_BRIDGE:
        return "Container requests host bridge access (network: bridge)"
    return None


def evaluate_deploy_risk(blueprint: Any) -> Dict[str, Any]:
    network_mode = getattr(blueprint, "network", NetworkMode.INTERNAL)
    try:
        network_mode = network_mode if isinstance(network_mode, NetworkMode) else NetworkMode(str(network_mode))
    except Exception:
        network_mode = NetworkMode.INTERNAL
    cap_add = [str(item).strip().upper() for item in (getattr(blueprint, "cap_add", []) or []) if str(item or "").strip()]
    security_opt = [str(item).strip() for item in (getattr(blueprint, "security_opt", []) or []) if str(item or "").strip()]
    cap_drop = [str(item).strip().upper() for item in (getattr(blueprint, "cap_drop", []) or []) if str(item or "").strip()]
    privileged = bool(getattr(blueprint, "privileged", False))
    read_only_rootfs = bool(getattr(blueprint, "read_only_rootfs", False))
    reasons: List[str] = []
    risk_flags: List[str] = []
    network_reason = check_needs_approval(network_mode)
    if network_reason:
        reasons.append(network_reason)
        risk_flags.append("network_full" if network_mode == NetworkMode.FULL else "network_bridge")
    for capability in cap_add:
        if capability in DANGEROUS_CAPABILITIES:
            reasons.append(f"Container requests dangerous capability: {capability}")
            risk_flags.append(f"cap_add:{capability}")
    for opt in security_opt:
        if opt.lower() in DANGEROUS_SECURITY_OPTS:
            reasons.append(f"Container relaxes runtime security: {opt}")
            risk_flags.append(f"security_opt:{opt.lower()}")
    if privileged:
        reasons.append("Container requests privileged mode")
        risk_flags.append("privileged")
    return {
        "requires_approval": bool(reasons),
        "reasons": reasons,
        "risk_flags": risk_flags,
        "network_mode": network_mode.value,
        "cap_add": cap_add,
        "security_opt": security_opt,
        "cap_drop": cap_drop,
        "privileged": privileged,
        "read_only_rootfs": read_only_rootfs,
    }
