"""Callback bindings shared by the TaskLoop pipeline stage."""
import functools
from typing import Any, Callable

from core.pipeline.plan_contract_validator import (
    issue_followup_step_receipt,
    issue_initial_step_receipt,
)


def build_step_receipt_issuer(
    context: Any,
    initial_issuer: Callable = issue_initial_step_receipt,
    followup_issuer: Callable = issue_followup_step_receipt,
) -> Callable[[Any, Any], Any]:
    def _issue(step: Any, predecessor: Any) -> Any:
        step_id = str(getattr(step, "step_id", "") or "")
        return (
            initial_issuer(step_id, context=context)
            if predecessor is None
            else followup_issuer(step_id, predecessor, context=context)
        )
    return _issue


def bind_replan_context(fn: Any, available_tools: Any, orchestrator_context: Any) -> Any:
    if available_tools is None and orchestrator_context is None:
        return fn

    @functools.wraps(fn)
    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("available_tools", available_tools)
        kwargs.setdefault("orchestrator_context", orchestrator_context)
        return fn(*args, **kwargs)

    return _wrapped
