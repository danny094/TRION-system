from __future__ import annotations

import shlex
from typing import Any

from blueprint_store import get_blueprint
from container_reference import ContainerReferenceError, resolve_container_reference
from contracts import error_result

MAX_EXEC_OUTPUT = 8000
EXEC_TIMEOUT_EXIT_CODE = 124
EXEC_TIMEOUT_MARKER = "__TRION_EXEC_TIMEOUT__"


def _client():
    from docker import from_env

    return from_env()


def _is_not_found(error: Exception) -> bool:
    return error.__class__.__name__ == "NotFound"


def _allowed_exec(blueprint_id: str) -> list[str]:
    detail = get_blueprint(blueprint_id)
    if not isinstance(detail, dict) or bool(detail.get("ok") is False):
        return []
    blueprint = detail.get("blueprint")
    if not isinstance(blueprint, dict):
        return []
    definition = blueprint.get("definition")
    if not isinstance(definition, dict):
        return []
    values = definition.get("allowed_exec")
    return [str(item).strip() for item in list(values or []) if str(item).strip()]


def _check_exec_policy(container: Any, command: str) -> dict[str, Any] | None:
    blueprint_id = str((container.labels or {}).get("trion.blueprint") or "").strip()
    if not blueprint_id:
        return None
    allowed = _allowed_exec(blueprint_id)
    if not allowed:
        return None
    cmd_prefix = str(command or "").strip().split()[0] if str(command or "").strip() else ""
    if cmd_prefix not in allowed:
        return error_result(
            "ACTION_NOT_ALLOWED",
            f"policy_denied: '{cmd_prefix or '?'}' not in allowed_exec for '{blueprint_id}'",
        )
    return None


def _build_timed_exec_command(command: str, timeout: int) -> str:
    timeout_s = max(1, int(timeout or 30))
    cmd_escaped = shlex.quote(str(command or ""))
    marker = EXEC_TIMEOUT_MARKER
    script = (
        f"cmd={cmd_escaped}; "
        "flag=/tmp/.trion_exec_timeout_$$; "
        'sh -lc "$cmd" & cmd_pid=$!; '
        '(SP=; trap \'kill "$SP" 2>/dev/null; exit\' TERM; '
        f'sleep {timeout_s} & SP=$!; wait "$SP"; '
        'echo 1 > "$flag"; kill -TERM "$cmd_pid" 2>/dev/null; '
        'SP=; sleep 1 & SP=$!; wait "$SP"; '
        'kill -KILL "$cmd_pid" 2>/dev/null) & killer_pid=$!; '
        'wait "$cmd_pid"; rc=$?; '
        'if [ -f "$flag" ]; then rm -f "$flag"; '
        'kill "$killer_pid" 2>/dev/null || true; wait "$killer_pid" 2>/dev/null || true; '
        f'echo "{marker}" >&2; exit {EXEC_TIMEOUT_EXIT_CODE}; fi; '
        'kill "$killer_pid" 2>/dev/null || true; wait "$killer_pid" 2>/dev/null || true; '
        'exit "$rc"'
    )
    return f"sh -lc {shlex.quote(script)}"


def _extract_timeout_marker(stderr: str) -> tuple[str, bool]:
    text = str(stderr or "")
    if EXEC_TIMEOUT_MARKER not in text:
        return text, False
    return text.replace(EXEC_TIMEOUT_MARKER, "").strip(), True


def _exec_run_with_workdir_fallback(container: Any, timed_command: str):
    result = container.exec_run(timed_command, demux=True, workdir="/workspace")
    try:
        stderr = (result.output[1] or b"").decode("utf-8", errors="replace") if isinstance(result.output, tuple) else ""
    except Exception:
        stderr = ""
    if int(getattr(result, "exit_code", 0) or 0) != 127 or "chdir to cwd" not in stderr.lower():
        return result
    return container.exec_run(timed_command, demux=True, workdir="/")


def exec_in_container(container_id: str = "", command: str = "", timeout: int = 30, container_name: str = "") -> dict[str, Any]:
    try:
        container = resolve_container_reference(_client(), container_id=container_id, container_name=container_name)
        if str(getattr(container, "status", "") or "").strip().lower() != "running":
            return {
                "exit_code": -1,
                "output": f"Container is not running (status: {container.status})",
                "container_id": str(getattr(container, "id", "") or container_id or container_name),
            }
        blocked = _check_exec_policy(container, command)
        if blocked:
            return blocked
        timed_cmd = _build_timed_exec_command(command, timeout)
        result = _exec_run_with_workdir_fallback(container, timed_cmd)
        stdout = (result.output[0] or b"").decode("utf-8", errors="replace") if result.output[0] else ""
        stderr = (result.output[1] or b"").decode("utf-8", errors="replace") if result.output[1] else ""
        stderr, timed_out = _extract_timeout_marker(stderr)
        exit_code = int(getattr(result, "exit_code", 0) or 0)
        if timed_out:
            exit_code = EXEC_TIMEOUT_EXIT_CODE
            stderr = f"{stderr}\nCommand timed out after {max(1, int(timeout or 30))}s" if stderr else f"Command timed out after {max(1, int(timeout or 30))}s"
        output = (stdout + ("\n" + stderr if stderr else "")).strip()
        return {"exit_code": exit_code, "output": output, "container_id": str(getattr(container, "id", "") or container_id or container_name), "timed_out": timed_out}
    except ContainerReferenceError as exc:
        return error_result("INVALID_CONTAINER_REFERENCE", str(exc))
    except Exception as exc:
        if _is_not_found(exc):
            return {"exit_code": -1, "output": "Container not found", "container_id": container_id or container_name}
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def exec_in_container_detailed(container_id: str = "", command: str = "", timeout: int = 30, container_name: str = "") -> dict[str, Any]:
    try:
        container = resolve_container_reference(_client(), container_id=container_id, container_name=container_name)
        if str(getattr(container, "status", "") or "").strip().lower() != "running":
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Container is not running (status: {container.status})",
                "truncated": False,
                "container_id": str(getattr(container, "id", "") or container_id or container_name),
            }
        blocked = _check_exec_policy(container, command)
        if blocked:
            return blocked
        timed_cmd = _build_timed_exec_command(command, timeout)
        result = _exec_run_with_workdir_fallback(container, timed_cmd)
        stdout = (result.output[0] or b"").decode("utf-8", errors="replace") if result.output[0] else ""
        stderr = (result.output[1] or b"").decode("utf-8", errors="replace") if result.output[1] else ""
        stderr, timed_out = _extract_timeout_marker(stderr)
        exit_code = int(getattr(result, "exit_code", 0) or 0)
        if timed_out:
            exit_code = EXEC_TIMEOUT_EXIT_CODE
            stderr = f"{stderr}\nCommand timed out after {max(1, int(timeout or 30))}s" if stderr else f"Command timed out after {max(1, int(timeout or 30))}s"
        truncated = len(stdout) > MAX_EXEC_OUTPUT or len(stderr) > MAX_EXEC_OUTPUT
        return {
            "exit_code": exit_code,
            "stdout": stdout[:MAX_EXEC_OUTPUT].strip(),
            "stderr": stderr[:MAX_EXEC_OUTPUT].strip(),
            "truncated": truncated,
            "timed_out": timed_out,
            "container_id": str(getattr(container, "id", "") or container_id or container_name),
        }
    except ContainerReferenceError as exc:
        return error_result("INVALID_CONTAINER_REFERENCE", str(exc))
    except Exception as exc:
        if _is_not_found(exc):
            return {"exit_code": -1, "stdout": "", "stderr": "Container not found", "truncated": False, "container_id": container_id or container_name}
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)
