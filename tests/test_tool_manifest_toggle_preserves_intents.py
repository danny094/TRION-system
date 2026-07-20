"""P11 SP3-E - Beweis: Toggle/Update darf einen bereits installierten,
vollstaendigen v2-Tool-Intents-Mirror nicht auf None wischen, nur weil die
Bundle-Datei tool_intents.json beim Toggle/Update-Aufruf nicht (mehr)
existiert.

Danny-Auftrag (SP3-E): "Unvollstaendige Registry-/Config-Daten duerfen
vollstaendige Bundle-/Mirror-Metadaten nicht kaputt-... ueberschreiben oder
verloren gehen."

Read-only-Inventar (SP3-E) zeigte: mcp.installer_manage_config.
preserve_tool_intents() schreibt normalized["tool_intents"] NUR, wenn
custom_mcp_dir(name)/tool_intents.json beim Aufruf existiert. Fehlt die
Datei (z.B. Bundle-Drift nach Install), bleibt normalized ohne
"tool_intents"-Schluessel. mcp.installer_registry.registry_entry_from_config()
liest dann config.get("tool_intents") -> None, und
mcp.installer_registry.upsert_registry_entry() ersetzt den Registry-Eintrag
VOLLSTAENDIG (kein Merge) - ein zuvor gueltiger, vollstaendiger v2-Mirror
wird dadurch unwiderruflich auf None gesetzt, obwohl Toggle/Update inhaltlich
nichts an den Tool-Capabilities aendern wollte.

Dieser Test reproduziert den von toggle_mcp()/update_mcp_config_payload()
(mcp/installer_manage_routes.py) durchlaufenen Aufrufpfad mit echten Dateien.
"""
from __future__ import annotations

import json

from mcp.installer_manage_config import (
    apply_config_and_registry_update,
    preserve_runtime_context,
    preserve_tool_intents,
)
from mcp.installer_manifest import normalize_manifest_payload


def _complete_v2_tool() -> dict:
    return {
        "name": "container_inspect",
        "description": "Inspect a container.",
        "domain": "container_runtime",
        "operation": "inspect",
        "requires": ["container_id_or_name"],
        "evidence_types": ["runtime_metadata"],
        "risk": "read_only",
        "target_scopes": ["runtime_state"],
        "freshness_support": "live_only",
        "tool_role": "primary",
        "output_schema": "mcp_output_schema",
    }


def _legacy_config(name: str) -> dict:
    return {
        "tier": "simple",
        "name": name,
        "url": "http://container-commander:8000/mcp",
        "description": "Container Commander",
        "enabled": True,
    }


def test_toggle_preserves_complete_v2_mirror_when_bundle_tool_intents_file_is_missing(
    monkeypatch, tmp_path
):
    import mcp.config as mcp_config

    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path))
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", tmp_path / "mcp_registry.json")

    name = "container-commander"
    bundle_dir = tmp_path / name
    bundle_dir.mkdir()
    config_path = bundle_dir / "config.json"
    config_path.write_text(json.dumps(_legacy_config(name)), encoding="utf-8")

    intents_path = bundle_dir / "tool_intents.json"
    intents_path.write_text(
        json.dumps({"schema_version": 2, "tools": [_complete_v2_tool()]}),
        encoding="utf-8",
    )

    # Install-Schritt (entspricht load_bundle_manifest()): vollstaendiger
    # v2-Mirror landet im ersten Registry-Eintrag.
    install_config = _legacy_config(name)
    install_normalized = normalize_manifest_payload("config.json", install_config)
    preserve_tool_intents(name, install_normalized)
    assert install_normalized["tool_intents"]["tools"][0]["capability_complete"] is True
    apply_config_and_registry_update(name, install_config, install_normalized)

    registry_after_install = mcp_config.get_all_mcps()
    installed_mirror = registry_after_install[name]["tool_intents"]
    assert installed_mirror["tools"][0]["domain"] == "container_runtime"

    # Bundle-Drift: tool_intents.json verschwindet (z.B. unvollstaendiges
    # Redeploy/Cleanup), Rest des Bundles bleibt unveraendert.
    intents_path.unlink()

    # Toggle-Schritt (entspricht installer_manage_routes.toggle_mcp()):
    toggle_config = json.loads(config_path.read_text(encoding="utf-8"))
    toggle_config["enabled"] = not bool(toggle_config.get("enabled", True))
    toggle_normalized = normalize_manifest_payload("config.json", toggle_config)
    preserve_runtime_context(name, toggle_normalized)
    preserve_tool_intents(name, toggle_normalized)
    apply_config_and_registry_update(name, toggle_config, toggle_normalized)

    registry_after_toggle = mcp_config.get_all_mcps()
    assert registry_after_toggle[name]["tool_intents"] == installed_mirror
