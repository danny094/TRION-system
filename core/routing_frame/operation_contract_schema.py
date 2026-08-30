"""Canonical structured parser for persisted OperationContract data."""
from collections.abc import Mapping
from dataclasses import asdict, fields
from typing import Any, get_args, get_origin

from core.routing_frame.contracts import FieldProvenance, OperationContract, OperationTransition


def parse_operation_contract(value: Any) -> OperationContract | None:
    typed = value if type(value) is OperationContract else None
    if type(value) is OperationContract:
        try:
            value = asdict(value)
        except (TypeError, ValueError):
            return None
    if not isinstance(value, Mapping):
        return None
    names = {item.name for item in fields(OperationContract)}
    if set(value) != names:
        return None
    parsed: dict[str, Any] = {}
    for item in fields(OperationContract):
        parsed_value = _field_value(item.type, value[item.name])
        if parsed_value is _INVALID:
            return None
        parsed[item.name] = parsed_value
    try:
        contract = OperationContract(**parsed)
    except (TypeError, ValueError):
        return None
    if not _nonempty_string(contract.domain) or not _nonempty_string(contract.primary_operation):
        return None
    if contract.primary_operation not in contract.allowed_operations:
        return None
    return typed if typed is not None and typed == contract else contract


_INVALID = object()


def _field_value(annotation: Any, value: Any) -> Any:
    origin, args = get_origin(annotation), get_args(annotation)
    if annotation is str:
        return value if _clean_string(value) else _INVALID
    if annotation is bool:
        return value if type(value) is bool else _INVALID
    if origin is tuple and args == (str, Ellipsis):
        parsed = _string_tuple(value)
        return parsed if parsed is not None else _INVALID
    if origin is tuple and args == (OperationTransition, Ellipsis):
        parsed = _transition_tuple(value)
        return parsed if parsed is not None else _INVALID
    if origin in (dict, Mapping) and args == (str, FieldProvenance):
        parsed = _provenance(value)
        return parsed if parsed is not None else _INVALID
    return _INVALID


def _string_tuple(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, (list, tuple)) or any(
        type(item) is not str or not item or item != item.strip() for item in value
    ):
        return None
    return tuple(value)


def _transition_tuple(value: Any) -> tuple[OperationTransition, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result = []
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != {
            "source_operation", "target_operation", "required_evidence",
        }:
            return None
        evidence = _string_tuple(raw.get("required_evidence"))
        try:
            result.append(OperationTransition(
                raw.get("source_operation"), raw.get("target_operation"), evidence,
            ))
        except (TypeError, ValueError):
            return None
    return tuple(result)


def _provenance(value: Any) -> dict[str, FieldProvenance] | None:
    if not isinstance(value, Mapping):
        return None
    result: dict[str, FieldProvenance] = {}
    for key, raw in value.items():
        if type(key) is not str or not isinstance(raw, Mapping) or set(raw) != {"source", "confidence", "span"}:
            return None
        source, confidence, span = raw.get("source"), raw.get("confidence"), raw.get("span")
        if type(source) is not str or type(confidence) not in (int, float) or type(span) is not str:
            return None
        result[key] = FieldProvenance(source=source, confidence=float(confidence), span=span)
    return result


def _nonempty_string(value: Any) -> bool:
    return type(value) is str and bool(value) and value == value.strip()


def _clean_string(value: Any) -> bool:
    return type(value) is str and value == value.strip()
