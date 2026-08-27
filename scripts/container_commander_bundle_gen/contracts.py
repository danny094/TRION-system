from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    annotation: str | None
    has_default: bool
    default_repr: str | None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    source_module: str
    register_name: str
    description: str
    function_source: str
    parameters: tuple[ParameterSpec, ...]
    import_map: tuple[tuple[str, str, str], ...]
    output_schema: dict[str, Any]


@dataclass(frozen=True)
class SourceModuleSpec:
    name: str
    output_name: str
    path: Path
    tools: tuple[ToolSpec, ...]


@dataclass(frozen=True)
class BundleModuleSpec:
    name: str
    functions: frozenset[str]


@dataclass(frozen=True)
class ContainerReferenceContractSpec:
    tool_names: tuple[str, ...]
    input_schema: dict[str, Any]
    error_source: str
    normalizer_source: str


@dataclass(frozen=True)
class BuildContext:
    root: Path
    source_dir: Path
    bundle_dir: Path
    out_dir: Path
    metadata_path: Path
    metadata: dict[str, Any]
    tool_intents_path: Path
    tool_intents: dict[str, Any]
    output_schemas_path: Path
    output_schemas: dict[str, dict[str, Any]]
    container_reference_contract: ContainerReferenceContractSpec
    modules: tuple[SourceModuleSpec, ...]
    bundle_modules: dict[str, BundleModuleSpec]
