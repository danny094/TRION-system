"""Regression fuer core/orchestrator/contracts.py::ToolDescriptor.

P11.0 SP1 fuegt additiv `mirror_schema_version`, `mirror_source_sha256` und
`mirror_bundle_version` hinzu (Denormalisierung der Mirror-Header-Metadaten,
siehe mcp.installer_tool_intents.build_tool_intent_mirror). Diese Felder
werden in SP1 noch von niemandem befuellt - SP4 verdrahtet den Mirror-Pfad in
core/orchestrator/tools.py. Dieser Test sichert nur, dass die Erweiterung
behavior-neutral ist: bestehende Konstruktion ohne die neuen Felder bleibt
gueltig, Defaults sind eindeutig "kein Mirror-Wert vorhanden".
"""
from core.orchestrator.contracts import ToolDescriptor


def test_tool_descriptor_construction_without_mirror_fields_still_works():
    descriptor = ToolDescriptor(name="time_now", description="Return current time.")

    assert descriptor.mirror_schema_version is None
    assert descriptor.mirror_source_sha256 == ""
    assert descriptor.mirror_bundle_version == ""


def test_tool_descriptor_accepts_mirror_fields_explicitly():
    descriptor = ToolDescriptor(
        name="container_inspect",
        mirror_schema_version=2,
        mirror_source_sha256="a" * 64,
        mirror_bundle_version="2.1.0",
    )

    assert descriptor.mirror_schema_version == 2
    assert descriptor.mirror_source_sha256 == "a" * 64
    assert descriptor.mirror_bundle_version == "2.1.0"
