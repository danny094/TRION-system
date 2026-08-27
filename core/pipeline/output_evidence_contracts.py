"""Immutable contracts for the pipeline-owned output-evidence handoff."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, auto
import math
from types import MappingProxyType
from typing import Any


class OutputEvidenceState(Enum):
    NO_TASK_LOOP = auto()
    TASK_LOOP_INCOMPLETE = auto()
    COMPLETE_WITHOUT_VALIDATED_EVIDENCE = auto()
    COMPLETE_WITH_VALIDATED_EVIDENCE = auto()


@dataclass(frozen=True)
class OutputEvidenceItem:
    structured_content: Mapping[str, Any]

    def __post_init__(self) -> None:
        def freeze(value: Any) -> Any:
            if isinstance(value, Mapping):
                if not all(isinstance(key, str) for key in value):
                    raise TypeError("structured_content keys must be strings")
                return MappingProxyType({key: freeze(item) for key, item in value.items()})
            if isinstance(value, (list, tuple)):
                return tuple(freeze(item) for item in value)
            if isinstance(value, float) and not math.isfinite(value):
                raise TypeError("structured_content numbers must be finite")
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            raise TypeError("structured_content must be recursively JSON-compatible")

        if not isinstance(self.structured_content, Mapping):
            raise TypeError("structured_content must be a mapping")
        object.__setattr__(self, "structured_content", freeze(self.structured_content))


@dataclass(frozen=True)
class OutputExecutionAttestation:
    completed_step_ids: tuple[str, ...]
    operation_contract_fingerprint: str

    def __post_init__(self) -> None:
        if (
            not self.completed_step_ids
            or any(type(step_id) is not str or not step_id or step_id != step_id.strip() for step_id in self.completed_step_ids)
            or len(set(self.completed_step_ids)) != len(self.completed_step_ids)
        ):
            raise ValueError("completed_step_ids must be unique non-empty strings")
        if type(self.operation_contract_fingerprint) is not str or not self.operation_contract_fingerprint.strip():
            raise ValueError("operation_contract_fingerprint must be non-empty")


@dataclass(frozen=True)
class OutputEvidenceHandoff:
    state: OutputEvidenceState
    items: tuple[OutputEvidenceItem, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.state, OutputEvidenceState):
            raise TypeError("state must be OutputEvidenceState")
        items = tuple(self.items)
        if any(type(item) is not OutputEvidenceItem for item in items):
            raise TypeError("items must contain OutputEvidenceItem values")
        has_validated_evidence = self.state is OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE
        if has_validated_evidence != bool(items):
            raise ValueError("state contradicts validated evidence items")
        object.__setattr__(self, "items", items)
