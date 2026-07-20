"""Sanitized observe-only routing trace projection.

Builds Doc-10-safe metadata from the existing RoutingFrame. It never reads
user_text, tool names, LLM output, artifacts, or arguments, and no production
gate consumes this fingerprint.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

_MEANING_KEYS = (
    "speech_act",
    "predicate",
    "theme",
    "requested_details",
    "temporal",
    "polarity",
    "modality",
    "cardinality",
    "mutation_candidate",
    "ambiguity",
)


def routing_trace_event(frame: Any) -> dict[str, Any]:
    if not isinstance(frame, Mapping):
        return _unavailable_event()

    contract = frame.get("operation_contract")
    if not isinstance(contract, Mapping):
        return _unavailable_event()

    meaning = _meaning_projection(frame)
    return {
        "type": "routing_trace",
        "stage": "routing",
        "meaning_status": meaning.get("status", "unavailable"),
        "meaning_fingerprint": _meaning_fingerprint(meaning),
        "operation": _clean(contract.get("primary_operation")),
        "allowed_operations": _safe_list(contract.get("allowed_operations")),
        "allowed_transitions": _safe_list(contract.get("allowed_transitions")),
        "required_evidence": _safe_list(contract.get("required_evidence")),
        "target_bound": bool(_clean(contract.get("target"))),
        "scope_lock_present": bool(_clean(contract.get("scope_lock"))),
        "detail_fields": _safe_list(contract.get("detail_fields")),
    }


def _unavailable_event() -> dict[str, Any]:
    return {
        "type": "routing_trace",
        "stage": "routing",
        "meaning_status": "unavailable",
        "meaning_fingerprint": "",
        "operation": "",
        "allowed_operations": [],
        "allowed_transitions": [],
        "required_evidence": [],
        "target_bound": False,
        "scope_lock_present": False,
        "detail_fields": [],
    }


def _meaning_projection(frame: Mapping[str, Any]) -> dict[str, Any]:
    signals = frame.get("source_signals")
    trace = signals.get("meaning_shadow_trace") if isinstance(signals, Mapping) else None
    if not isinstance(trace, Mapping) or trace.get("status") != "ok":
        return {"status": "unavailable"}
    result = {"status": "ok"}
    for key in _MEANING_KEYS:
        result[key] = _normalized(trace.get(key))
    return result


def _meaning_fingerprint(projection: Mapping[str, Any]) -> str:
    if projection.get("status") != "ok":
        return ""
    encoded = json.dumps(dict(projection), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalized(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _normalized(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_normalized(v) for v in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    return _clean(value)


def _safe_list(value: Any) -> list[str]:
    return [_clean(item) for item in list(value or []) if _clean(item)]


def _clean(value: Any) -> str:
    return str(value or "").strip()
