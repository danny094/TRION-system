import json
import queue
import shlex
import subprocess
import threading
from typing import Dict, Any, List, Optional

from utils.logger import log_info, log_error, log_debug


class STDIOTransport:
    """STDIO Transport für lokale MCP-Prozesse."""

    def __init__(self, command: str, timeout: int = 30, cwd: str | None = None):
        self.command = command
        self.timeout = timeout
        self.cwd = cwd
        self.process: Optional[subprocess.Popen] = None
        self._response_queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False

    def _start_process(self):
        """Startet den MCP-Prozess."""
        if self.process is not None:
            return
        try:
            log_debug(f"[STDIO] Starting: {self.command}")
            self.process = subprocess.Popen(
                shlex.split(self.command),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=self.cwd or None,
            )
            self._running = True
            self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self._reader_thread.start()
            log_info(f"[STDIO] Process started: PID {self.process.pid}")
            self._initialize_process()
        except Exception as e:
            log_error(f"[STDIO] Failed to start: {e}")
            raise

    def _initialize_process(self) -> None:
        log_debug("[STDIO] Sending initialize...")
        self._write_payload(
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "trion-hub", "version": "1.0.0"},
                },
            }
        )
        init_response = self._wait_for_response(60)
        if "error" in init_response:
            raise Exception(f"Initialize failed: {init_response['error']}")
        self._write_payload(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        )
        log_debug("[STDIO] Initialize successful")

    def _write_payload(self, payload: Dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise Exception("STDIO process stdin is not available")
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()

    def _wait_for_response(self, timeout: int) -> Dict[str, Any]:
        try:
            return self._response_queue.get(timeout=timeout)
        except queue.Empty as exc:
            raise Exception("Timeout waiting for response") from exc

    def _read_output(self):
        """Liest stdout in separatem Thread."""
        while self._running and self.process:
            try:
                line = self.process.stdout.readline()
                if line:
                    try:
                        data = json.loads(line.strip())
                        self._response_queue.put(data)
                    except json.JSONDecodeError:
                        pass
                elif self.process.poll() is not None:
                    break
            except Exception as e:
                log_error(f"[STDIO] Read error: {e}")
                break

    def _send_request(self, payload: Dict) -> Dict:
        """Sendet Request und wartet auf Response."""
        self._start_process()
        try:
            self._write_payload(payload)
            return self._wait_for_response(self.timeout)
        except Exception as e:
            if "Timeout waiting for response" in str(e):
                log_error("[STDIO] Timeout waiting for response")
                return {"error": "Timeout"}
            log_error(f"[STDIO] Request failed: {e}")
            return {"error": str(e)}

    def list_tools(self) -> List[Dict[str, Any]]:
        """Holt Tool-Liste vom MCP."""
        response = self._send_request(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        result = response.get("result")
        if isinstance(result, dict) and "tools" in result:
            return result["tools"]
        if isinstance(result, list):
            return result
        return []

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Ruft ein Tool auf."""
        response = self._send_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }
        )
        if "error" in response:
            return {"error": response["error"]}
        return response.get("result", {})

    def health_check(self) -> bool:
        """Prüft ob MCP läuft."""
        try:
            if self.process is None:
                self._start_process()
            return self.process is not None and self.process.poll() is None
        except Exception:
            return False

    def shutdown(self):
        """Beendet den Prozess."""
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
