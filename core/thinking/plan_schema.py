"""Canonical structured parser for persisted ThinkingPlan data."""
from collections.abc import Mapping
from dataclasses import MISSING, fields
from enum import Enum
from types import UnionType
from typing import Any, Union, get_args, get_origin

from core.thinking.contracts import PlanStep, ThinkingPlan


def parse_thinking_plan(value: Any) -> ThinkingPlan | None:
    if type(value) is ThinkingPlan:
        return value
    parsed = _dataclass_value(ThinkingPlan, value)
    return parsed if type(parsed) is ThinkingPlan else None


_INVALID = object()


def _dataclass_value(contract_type: type, value: Any) -> Any:
    if type(value) is contract_type:
        return value
    if not isinstance(value, Mapping):
        return _INVALID
    contract_fields = fields(contract_type)
    names = {item.name for item in contract_fields}
    if not set(value).issubset(names):
        return _INVALID
    parsed: dict[str, Any] = {}
    for item in contract_fields:
        if item.name not in value:
            if item.default is MISSING and item.default_factory is MISSING:
                return _INVALID
            continue
        parsed_value = _field_value(item.type, value[item.name])
        if parsed_value is _INVALID:
            return _INVALID
        parsed[item.name] = parsed_value
    try:
        result = contract_type(**parsed)
    except (TypeError, ValueError):
        return _INVALID
    if type(result) is PlanStep:
        if not _nonempty_string(result.step_id):
            return _INVALID
        if result.tool is not None and not _nonempty_string(result.tool):
            return _INVALID
    return result


def _field_value(annotation: Any, value: Any) -> Any:
    origin, args = get_origin(annotation), get_args(annotation)
    if annotation is Any:
        return value
    if annotation is str:
        return value if type(value) is str else _INVALID
    if annotation is bool:
        return value if type(value) is bool else _INVALID
    if annotation is int:
        return value if type(value) is int else _INVALID
    if annotation is float:
        return value if type(value) in {int, float} else _INVALID
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        if type(value) is annotation:
            return value
        if type(value) is not str:
            return _INVALID
        try:
            return annotation(value)
        except ValueError:
            return _INVALID
    if origin in {Union, UnionType}:
        if value is None and type(None) in args:
            return None
        candidates = [item for item in args if item is not type(None)]
        if len(candidates) != 1:
            return _INVALID
        return _field_value(candidates[0], value)
    if origin is list and len(args) == 1:
        if type(value) is not list:
            return _INVALID
        result = [_field_value(args[0], item) for item in value]
        return _INVALID if any(item is _INVALID for item in result) else result
    if origin is dict and len(args) == 2:
        if type(value) is not dict:
            return _INVALID
        result: dict[Any, Any] = {}
        for key, item in value.items():
            parsed_key = _field_value(args[0], key)
            parsed_item = _field_value(args[1], item)
            if parsed_key is _INVALID or parsed_item is _INVALID:
                return _INVALID
            result[parsed_key] = parsed_item
        return result
    if isinstance(annotation, type) and hasattr(annotation, "__dataclass_fields__"):
        return _dataclass_value(annotation, value)
    return _INVALID


def _nonempty_string(value: Any) -> bool:
    return type(value) is str and bool(value) and value == value.strip()
