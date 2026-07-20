import inspect
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from adapters.task_resume_serialization import plan_from_dict, snapshot_from_dict
from adapters.task_resume_store import (
    cancel_waiting_task, claim_waiting_task, finalize_claimed_failure,
    finalize_claimed_task, get_task_record,
)
from adapters.tool_runner_bridge import get_available_tools, make_tool_runner
from core.pipeline.common import public_task_artifacts, public_task_loop_snapshot
from core.pipeline.operation_contract_context import ReceiptConfigurationState, receipt_configuration_state
from core.pipeline.plan_contract_validator import bind_validated_replanner, validate_plan_contract
from core.pipeline.public_projection import public_internal_error, public_plan_contract_error
from core.pipeline.receipt_preflight import preflight_current_step_receipt
from core.pipeline.task_loop_stage import (
    _bind_replan_context, build_step_receipt_issuer, build_step_receipt_validator,
    build_step_receipt_validator_factory,
)
from core.orchestrator.tools import list_available_tools
from core.task_loop.executable_now import details_by_name
from core.task_loop.contracts import StopReason, TaskLoopState
from utils.logger import log_debug, log_error

router = APIRouter(tags=["tasks"])


class TaskApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_text: str = "approve"


def continue_task_loop(*args, **kwargs):
    from core.task_loop.task_loop import continue_task_loop as _continue_task_loop

    return _continue_task_loop(*args, **kwargs)


def build_replan(*args, **kwargs):
    from core.thinking.replanner import build_replan as _build_replan

    return _build_replan(*args, **kwargs)


@router.post("/api/tasks/{task_id}/approve")
async def approve_task(task_id: str, request: TaskApproveRequest):
    record = get_task_record(task_id)
    if not isinstance(record, dict):
        raise HTTPException(status_code=404, detail="task_not_found")
    if record.get("status") != TaskLoopState.WAITING.value:
        raise HTTPException(status_code=409, detail="task_not_waiting")

    plan_raw = record.get("plan")
    snapshot_raw = record.get("snapshot")
    if not isinstance(plan_raw, dict) or not isinstance(snapshot_raw, dict):
        raise HTTPException(status_code=409, detail="task_record_corrupt")

    try:
        plan = plan_from_dict(plan_raw)
        snapshot = snapshot_from_dict(snapshot_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=409, detail="task_record_corrupt") from None
    if snapshot.state != TaskLoopState.WAITING:
        raise HTTPException(status_code=409, detail="snapshot_not_waiting")

    persisted_context = _dict_value(record.get("orchestrator_context"))
    stored_fingerprint = record.get("operation_contract_fingerprint")
    configuration = receipt_configuration_state(
        persisted_context,
        receipt_provenance=(
            bool(snapshot.step_operation_executions)
            or stored_fingerprint is not None
        ),
        receipt_history_present="step_operation_executions" in snapshot_raw,
    )
    if configuration is ReceiptConfigurationState.INCONSISTENT_FAIL_CLOSED:
        return JSONResponse(public_plan_contract_error(), status_code=409)
    try:
        tools = list_available_tools(get_available_tools())
    except Exception:
        return JSONResponse(public_plan_contract_error(), status_code=409)
    plan_contract = validate_plan_contract(
        plan,
        tools,
        context=persisted_context,
        stored_fingerprint=stored_fingerprint,
        require_fingerprint=configuration is ReceiptConfigurationState.RECEIPT_MODE_ACTIVE,
    )
    if not plan_contract.allowed:
        return JSONResponse(public_plan_contract_error(), status_code=409)
    # P11 SP3-F Fund C: nur internes Logging, NICHT in den JSON-Response-Body
    # (Doc19/Doc38 WebUI-Vertrag bleibt unveraendert).
    log_debug(f"[tasks_routes] approve_task({task_id}): tool_truth_source=live_registry_mirror")
    replanner = bind_validated_replanner(
        _bind_replan_context(build_replan, tools, persisted_context),
        tools,
        context=persisted_context,
        stored_fingerprint=stored_fingerprint,
    )
    kwargs = {"tool_runner": make_tool_runner(), "replanner_fn": replanner}
    if _accepts_kwarg(continue_task_loop, "tool_details_by_name"):
        kwargs["tool_details_by_name"] = details_by_name(tools)
    if _accepts_kwarg(continue_task_loop, "operation_contract_fingerprint"):
        kwargs["operation_contract_fingerprint"] = stored_fingerprint
    if configuration is ReceiptConfigurationState.RECEIPT_MODE_ACTIVE:
        issuer = build_step_receipt_issuer(persisted_context)
        validator = build_step_receipt_validator(persisted_context, tools, plan)
        if not preflight_current_step_receipt(plan, snapshot, issuer, validator):
            return JSONResponse(public_plan_contract_error(), status_code=409)
        if _accepts_kwarg(continue_task_loop, "receipt_mode"):
            kwargs["receipt_mode"] = True
        if _accepts_kwarg(continue_task_loop, "step_receipts"):
            kwargs["step_receipts"] = {}
        if _accepts_kwarg(continue_task_loop, "receipt_issuer"):
            kwargs["receipt_issuer"] = issuer
        if _accepts_kwarg(continue_task_loop, "receipt_validator"):
            kwargs["receipt_validator"] = validator
        if _accepts_kwarg(continue_task_loop, "receipt_validator_factory"):
            kwargs["receipt_validator_factory"] = build_step_receipt_validator_factory(
                persisted_context, tools,
            )
    try:
        claimed = claim_waiting_task(task_id, expected_updated_at=str(record.get("updated_at") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="task_not_waiting") from exc
    if not isinstance(claimed, dict):
        raise HTTPException(status_code=404, detail="task_not_found")
    claim_version = claimed.get("updated_at")
    try:
        result = continue_task_loop(snapshot, request.user_text, plan, **kwargs)
        finalized = finalize_claimed_task(task_id, result, expected_updated_at=claim_version)
    except Exception as exc:
        log_error(f"[tasks_routes] claimed task continuation failed: {exc!r}")
        try:
            finalize_claimed_failure(task_id, expected_updated_at=claim_version)
        except Exception as finalize_exc:
            log_error(f"[tasks_routes] claimed task failure finalization failed: {finalize_exc!r}")
        return JSONResponse(public_internal_error(), status_code=500)
    if not isinstance(finalized, dict):
        return JSONResponse(public_internal_error(), status_code=409)
    return {
        "state": result.state.value,
        "stop_reason": result.stop_reason.value if result.stop_reason else None,
        "visible_content": result.visible_content,
        "artifacts": public_task_artifacts(result.artifacts),
        "snapshot": public_task_loop_snapshot(result.snapshot),
    }


@router.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    try:
        record = cancel_waiting_task(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="task_not_waiting") from exc
    if not isinstance(record, dict):
        raise HTTPException(status_code=404, detail="task_not_found")
    return {
        "state": TaskLoopState.CANCELLED.value,
        "stop_reason": StopReason.USER_CANCELLED.value,
    }


def _dict_value(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _accepts_kwarg(fn: Any, name: str) -> bool:
    params = inspect.signature(fn).parameters
    return name in params or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
