from dataclasses import dataclass, field
from enum import Enum, auto
from types import MappingProxyType
from typing import Any, Callable, Dict, Mapping


def _freeze_output_schema(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_output_schema(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_output_schema(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_output_schema(item) for item in value)
    return value


def _plain_output_schema(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain_output_schema(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_output_schema(item) for item in value]
    return value


@dataclass(frozen=True)
class TaskToolCall:
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    step_id: str = ""
    timeout_s: float = 30.0
    output_schema: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.output_schema is not None and not isinstance(self.output_schema, Mapping):
            raise TypeError("output_schema must be a mapping or None")
        object.__setattr__(self, "output_schema", _freeze_output_schema(self.output_schema))

    def output_schema_mapping(self) -> dict[str, Any] | None:
        if self.output_schema is None:
            return None
        return _plain_output_schema(self.output_schema)


_TASK_TOOL_RESULT_MISSING = object()


class TaskToolResultStatus(Enum):
    SUCCESS_MISSING, SUCCESS_EMPTY, SUCCESS_VALUE = auto(), auto(), auto()
    TOOL_FAILURE, PROTOCOL_FAILURE, TRANSPORT_FAILURE = auto(), auto(), auto()


class TaskStructuralValidationStatus(Enum):
    MISSING, UNVERIFIED, VALID, INVALID = auto(), auto(), auto(), auto()


@dataclass(frozen=True, init=False)
class TaskToolResult:
    status: TaskToolResultStatus
    result: Dict[str, Any]
    error: str | None
    structural_result: object | None
    structural_validation_status: TaskStructuralValidationStatus

    def __init__(
        self,
        success: Any = _TASK_TOOL_RESULT_MISSING,
        result: Any = _TASK_TOOL_RESULT_MISSING,
        error: str | None = None,
        *,
        status: TaskToolResultStatus | None = None,
        structural_result: object | None = None,
        structural_validation_status: TaskStructuralValidationStatus | None = None,
    ) -> None:
        if status is None:
            if not isinstance(success, bool):
                raise TypeError("legacy success must be bool")
            if not success:
                status = TaskToolResultStatus.TOOL_FAILURE
            elif result is _TASK_TOOL_RESULT_MISSING:
                status = TaskToolResultStatus.SUCCESS_MISSING
            elif not isinstance(result, Mapping):
                raise TypeError("result must be a mapping")
            else:
                status = TaskToolResultStatus.SUCCESS_VALUE if result else TaskToolResultStatus.SUCCESS_EMPTY
        elif success is not _TASK_TOOL_RESULT_MISSING:
            raise TypeError("success and status are mutually exclusive")
        if not isinstance(status, TaskToolResultStatus):
            raise TypeError("status must be TaskToolResultStatus")
        if result is _TASK_TOOL_RESULT_MISSING:
            result = {}
        if not isinstance(result, Mapping):
            raise TypeError("result must be a mapping")
        if structural_validation_status is None:
            structural_validation_status = (
                TaskStructuralValidationStatus.MISSING
                if structural_result is None
                else TaskStructuralValidationStatus.UNVERIFIED
            )
        if not isinstance(structural_validation_status, TaskStructuralValidationStatus):
            raise TypeError("structural_validation_status must be TaskStructuralValidationStatus")
        if structural_validation_status is TaskStructuralValidationStatus.MISSING and structural_result is not None:
            raise ValueError("missing structural validation status contradicts structural result")
        if structural_validation_status is not TaskStructuralValidationStatus.MISSING and structural_result is None:
            raise ValueError("structural validation status requires structural result")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "result", dict(result))
        object.__setattr__(self, "error", error)
        object.__setattr__(self, "structural_result", structural_result)
        object.__setattr__(self, "structural_validation_status", structural_validation_status)

    @property
    def success(self) -> bool:
        return self.status in {
            TaskToolResultStatus.SUCCESS_MISSING,
            TaskToolResultStatus.SUCCESS_EMPTY,
            TaskToolResultStatus.SUCCESS_VALUE,
        }


ToolRunner = Callable[[TaskToolCall], TaskToolResult]
TaskLoopEventSink = Callable[[dict[str, Any]], None]
