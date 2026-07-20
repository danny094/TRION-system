from typing import List

from core.orchestrator.contracts import ToolDescriptor

# Tools mit dieser Rolle werden nie an die Planung übergeben (Doc 36 Regel 2+3).
# Liest aus tool.tool_role — kein hardcodierter Tool-Name.
_FORBIDDEN_DIRECT_ROLE = "forbidden_direct"


def filter_tools(
    available: List[ToolDescriptor],
    allowlist: List[str],
    blocklist: List[str],
) -> List[ToolDescriptor]:
    """Filter available tools by allowlist, blocklist, and planning eligibility.

    allowlist: if non-empty, only tools whose name is in the list pass through.
    blocklist: tools whose name is in the list are always removed.
    forbidden_direct: tools with tool_role='forbidden_direct' are always removed
    from the planning surface, regardless of allowlist/blocklist (Doc 36 Regel 3).
    """
    result = list(available)
    if allowlist:
        allowed = set(allowlist)
        result = [t for t in result if t.name in allowed]
    if blocklist:
        blocked = set(blocklist)
        result = [t for t in result if t.name not in blocked]
    result = [t for t in result if t.tool_role != _FORBIDDEN_DIRECT_ROLE]
    return result
