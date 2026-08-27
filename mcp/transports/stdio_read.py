"""Single STDIO line parser for P13 read observations."""

import json
from collections.abc import Mapping

from mcp.protocol_contracts import MCPSTDIOReadObservation, MCPSTDIOReadStatus


def parse_stdio_read_line(line: str) -> MCPSTDIOReadObservation:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return MCPSTDIOReadObservation(MCPSTDIOReadStatus.MALFORMED_RESPONSE)
    if not isinstance(payload, Mapping):
        return MCPSTDIOReadObservation(MCPSTDIOReadStatus.MALFORMED_RESPONSE)
    return MCPSTDIOReadObservation(MCPSTDIOReadStatus.JSON_MESSAGE, payload=payload)
