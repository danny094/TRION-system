from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.classifier.contracts import ClassifierResult


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    description: str = ""
    source: str = ""
    schema: Dict[str, Any] = field(default_factory=dict)
    intent_description: str = ""
    intent_examples: List[str] = field(default_factory=list)
    intent_keywords: List[str] = field(default_factory=list)
    capability_domain: str = ""
    capability_operation: str = ""
    capability_entity_types: List[str] = field(default_factory=list)
    capability_evidence_types: List[str] = field(default_factory=list)
    capability_required_args: List[str] = field(default_factory=list)
    capability_risk: str = ""
    capability_target_scopes: List[str] = field(default_factory=list)
    capability_freshness_support: str = ""
    # SP3-D (2026-06-28, Codex-Fund SP3-C): Registry-Mirror-Referenz auf das
    # Live-MCP-outputSchema (Sentinel "mcp_output_schema", siehe
    # mcp.installer_tool_intents._output_schema_reference()). Vorher am
    # Mirror-Gate validiert, aber nie auf ToolDescriptor projiziert.
    capability_output_schema: str = ""
    output_schema: Dict[str, Any] = field(default_factory=dict)
    tool_role: str = "primary"
    can_answer_directly: bool = True
    # P11.0 SP4: aus dem per-Tool `tool_intent_meta` des Registry Mirrors
    # denormalisiert (siehe mcp.installer_tool_intents.build_tool_intent_mirror,
    # core/orchestrator/tool_descriptor_projection.py::descriptor_from_raw()).
    mirror_schema_version: Optional[int] = None
    mirror_source_sha256: str = ""
    mirror_bundle_version: str = ""


@dataclass(frozen=True)
class OrchestratorPackage:
    available_tools: List[ToolDescriptor]
    selected_tools: List[ToolDescriptor]
    context: Dict[str, Any]
    classifier_result: ClassifierResult
