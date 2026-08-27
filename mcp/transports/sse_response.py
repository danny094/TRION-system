"""Response decoding for the standalone SSE transport."""

import json
from collections.abc import Mapping
from typing import Any, Optional

from mcp.protocol_contracts import (
    MCPTransportProtocolFailureKind as FailureKind,
    MCPTransportRequestOutcome,
    MCPTransportRequestStatus as RequestStatus,
)


def decode_sse_event(line: str) -> Optional[Any]:
    if not line.startswith("data: "):
        return None
    try:
        return json.loads(line[6:])
    except json.JSONDecodeError:
        return None


def decode_sse_tool_result_envelope(result: Any) -> MCPTransportRequestOutcome:
    if not isinstance(result, Mapping):
        return MCPTransportRequestOutcome(
            RequestStatus.PROTOCOL_FAILURE,
            protocol_failure_kind=FailureKind.MALFORMED_RESPONSE,
        )
    return MCPTransportRequestOutcome(RequestStatus.OK, payload=result)
