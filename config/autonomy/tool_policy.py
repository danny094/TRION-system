"""
config.autonomy.tool_policy
============================
Tool-Policy für autonome Ausführung — Allowlist, Blocklist, Approval-Pflicht.

Steuert welche Tools TRION autonom aufrufen darf:
- AUTONOMY_TOOL_ALLOWLIST: nur diese Tools erlaubt (leer = alle erlaubt)
- AUTONOMY_TOOL_BLOCKLIST: diese Tools immer geblockt
- AUTONOMY_APPROVAL_REQUIRED_TOOLS: User-Freigabe vor Ausführung nötig
"""
import os

from config.infra.adapter import settings


def _parse_list(raw: str) -> list[str]:
    return [s.strip() for s in str(raw or "").split(",") if s.strip()]


def get_autonomy_tool_allowlist() -> list[str]:
    """Tool-Allowlist für autonome Ausführung. Leer = alle verfügbaren Tools erlaubt."""
    raw = settings.get("AUTONOMY_TOOL_ALLOWLIST", os.getenv("AUTONOMY_TOOL_ALLOWLIST", ""))
    return _parse_list(str(raw or ""))


def get_autonomy_tool_blocklist() -> list[str]:
    """Tool-Blocklist für autonome Ausführung. Leer = kein Tool geblockt."""
    raw = settings.get("AUTONOMY_TOOL_BLOCKLIST", os.getenv("AUTONOMY_TOOL_BLOCKLIST", ""))
    return _parse_list(str(raw or ""))


def get_autonomy_approval_required_tools() -> list[str]:
    """Tools die vor Ausführung eine explizite User-Freigabe benötigen."""
    raw = settings.get(
        "AUTONOMY_APPROVAL_REQUIRED_TOOLS",
        os.getenv("AUTONOMY_APPROVAL_REQUIRED_TOOLS", ""),
    )
    return _parse_list(str(raw or ""))
