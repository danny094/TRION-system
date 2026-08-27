import json
import queue
import shlex
import subprocess
import threading
from collections.abc import Mapping
from typing import Any, Dict, List, Optional

from mcp.protocol_negotiation_contracts import (
    SUPPORTED_MCP_PROTOCOL_VERSION,
    MCPProtocolNegotiationStatus as NegotiationStatus,
    validate_protocol_version,
)
from mcp.protocol_contracts import (
    MCPSTDIOReadObservation,
    MCPSTDIOReadStatus as ReadStatus,
    MCPSTDIORequestObservation,
    MCPToolsListProtocolStatus as ListStatus,
    MCPTransportProtocolFailureKind as FailureKind,
    MCPTransportRequestOutcome,
    MCPTransportRequestStatus as RequestStatus,
)
from mcp.protocol_tools_list import project_tools_list_response
from mcp.tool_result_contracts import MCPToolResultEnvelope, project_tool_result_envelope
from mcp.transports.stdio_read import parse_stdio_read_line
from utils.logger import log_debug, log_error, log_info


class STDIOTransport:
    def __init__(self, command: str, timeout: int = 30, cwd: str | None = None):
        self.command = command
        self.timeout = timeout
        self.cwd = cwd
        self.process: Optional[subprocess.Popen] = None
        self._response_queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False

    def _start_process(self):
        if self.process is not None:
            return
        try:
            log_debug(f"[STDIO] Starting: {self.command}")
            self.process = subprocess.Popen(
                shlex.split(self.command), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1, cwd=self.cwd or None,
            )
            self._running = True
            self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self._reader_thread.start()
            log_info(f"[STDIO] Process started: PID {self.process.pid}")
            self._initialize_process()
        except Exception as exc:
            log_error(f"[STDIO] Failed to start: {exc}")
            raise

    def _initialize_process(self) -> None:
        log_debug("[STDIO] Sending initialize...")
        self._write_payload({
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {
                "protocolVersion": SUPPORTED_MCP_PROTOCOL_VERSION, "capabilities": {},
                "clientInfo": {"name": "trion-hub", "version": "1.0.0"},
            },
        })
        observation = self._wait_for_response(60)
        outcome = self._outcome_from_read_observation(observation)
        if outcome.status is not RequestStatus.OK:
            raise Exception(f"Initialize failed: {self._failure_text(outcome)}")
        protocol_value = (
            outcome.payload.get("protocolVersion")
            if isinstance(outcome.payload, Mapping)
            else {}
        )
        negotiation = validate_protocol_version(protocol_value)
        if negotiation.status is not NegotiationStatus.NEGOTIATED:
            raise Exception(f"Initialize failed: {negotiation.status.name}")
        self._write_payload({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        log_debug("[STDIO] Initialize successful")

    def _write_payload(self, payload: Dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise Exception("STDIO process stdin is not available")
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()

    def _wait_for_response(self, timeout: int) -> MCPSTDIOReadObservation:
        try:
            return self._response_queue.get(timeout=timeout)
        except queue.Empty:
            return MCPSTDIOReadObservation(ReadStatus.READ_TIMEOUT, transport_diagnostic="Timeout waiting for response")

    def _read_output(self):
        while self._running and self.process:
            try:
                line = self.process.stdout.readline()
                if line:
                    self._response_queue.put(parse_stdio_read_line(line.strip()))
                elif self.process.poll() is not None:
                    break
            except Exception as exc:
                log_error(f"[STDIO] Read error: {exc}")
                self._response_queue.put(MCPSTDIOReadObservation(ReadStatus.READ_FAILURE, transport_diagnostic=str(exc) or "STDIO transport failure"))
                break

    def _failure_text(self, outcome: MCPTransportRequestOutcome) -> str:
        if outcome.status is RequestStatus.TRANSPORT_FAILURE:
            return outcome.transport_diagnostic or "STDIO transport failure"
        if outcome.protocol_failure_kind is FailureKind.JSON_RPC_ERROR:
            return str(dict(outcome.protocol_error or {}))
        return "Malformed MCP response"

    def _outcome_from_read_observation(self, observation: MCPSTDIOReadObservation) -> MCPTransportRequestOutcome:
        if observation.status is ReadStatus.READ_FAILURE:
            return MCPTransportRequestOutcome(RequestStatus.TRANSPORT_FAILURE, transport_diagnostic=observation.transport_diagnostic or "STDIO transport failure")
        if observation.status is ReadStatus.READ_TIMEOUT:
            return MCPTransportRequestOutcome(RequestStatus.TRANSPORT_FAILURE, transport_diagnostic=observation.transport_diagnostic or "Timeout waiting for response")
        if observation.status is ReadStatus.MALFORMED_RESPONSE:
            return MCPTransportRequestOutcome(RequestStatus.PROTOCOL_FAILURE, protocol_failure_kind=FailureKind.MALFORMED_RESPONSE)
        envelope = observation.payload or {}
        if envelope.get("result") is not None:
            return MCPTransportRequestOutcome(RequestStatus.OK, payload=envelope["result"])
        if hasattr(envelope.get("error"), "items"):
            return MCPTransportRequestOutcome(RequestStatus.PROTOCOL_FAILURE, protocol_failure_kind=FailureKind.JSON_RPC_ERROR, protocol_error=envelope["error"])
        return MCPTransportRequestOutcome(RequestStatus.PROTOCOL_FAILURE, protocol_failure_kind=FailureKind.MALFORMED_RESPONSE)

    def _send_request_outcome(self, payload: Dict) -> MCPSTDIORequestObservation:
        try:
            self._start_process()
            self._write_payload(payload)
            read_observation = self._wait_for_response(self.timeout)
        except Exception as exc:
            error_text = str(exc)
            log_error(f"[STDIO] Request failed: {exc}")
            outcome = MCPTransportRequestOutcome(RequestStatus.TRANSPORT_FAILURE, transport_diagnostic=error_text or "STDIO transport failure")
            return MCPSTDIORequestObservation(outcome)
        legacy_envelope = read_observation if isinstance(read_observation, dict) else None
        if isinstance(read_observation, dict):
            read_observation = MCPSTDIOReadObservation(ReadStatus.JSON_MESSAGE, payload=read_observation)
        outcome = self._outcome_from_read_observation(read_observation)
        envelope = legacy_envelope or (
            read_observation.payload if outcome.status is not RequestStatus.PROTOCOL_FAILURE else None
        )
        return MCPSTDIORequestObservation(outcome, envelope)

    def list_tools_protocol_result(self):
        observation = self._send_request_outcome({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        return project_tools_list_response(observation.outcome)

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResultEnvelope:
        observation = self._send_request_outcome({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        })
        return project_tool_result_envelope(observation.outcome)

    def shutdown(self):
        self._running = False
        if not self.process:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
        self.process = None
        log_info("[STDIO] Process terminated")
