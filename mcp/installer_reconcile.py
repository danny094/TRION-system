"""
mcp.installer_reconcile
==========================
Reconciler fuer `mcp_registry.json` gegen den tatsaechlichen Bundle-/Receipt-
Zustand auf der Festplatte (P11.0 SP3).

Deckt drei Drift-Faelle ab (P11.0-Plan SP3):
- fehlender Mirror: ein installer-verwalteter Bundle besitzt eine
  tool_intents.json, der Registry-Eintrag hat aber keinen (oder einen
  veralteten) Mirror.
- hash-abweichender Mirror: die Bundle-tool_intents.json hat sich seit dem
  letzten Mirror-Build geaendert (anderer source_sha256).
- verwaister Eintrag: das Bundle-Verzeichnis eines zuvor installer-
  verwalteten MCPs existiert nicht mehr.

Codex DECIDE 1 (Reconciler-Trigger): laeuft automatisch genau einmal beim
Hub-Start, unmittelbar VOR `MCPHub.initialize()` die enabled MCP-Configs
liest - nicht bei jedem `reload_registry()` (Tool-Miss-Reloads liegen im
Request-Pfad und duerfen keinen vollen Bundle-Scan ausloesen). Reconciliation
ist idempotente Startup-Reparatur, kein Hot-Path.

Codex DECIDE 2 (Orphan-Scope): ein verwaister Eintrag wird nur dann komplett
entfernt, wenn `managed_by == MANAGED_BY_INSTALLER` bewiesen ist (gesetzt
ausschliesslich in mcp.installer_registry.registry_entry_from_config()).
Fehlen Bundle, Receipt UND Marker gleichzeitig, wird NICHT geraten/geloescht -
der Eintrag wird als `unresolved` gemeldet. Core-/Memory-Eintraege
(mcp.config.core_mcp_names()) tragen den Marker nie und werden hier komplett
ausgeklammert, statt als `unresolved` Rauschen zu erzeugen.

Codex DECIDE 3 (kein Hub-Reload hier): dieses Modul importiert/kontrolliert
den Hub nicht und ladet ihn nie neu - reine Registry-/Dateisystem-Reparatur.
Aufrufer, die gegen einen bereits initialisierten Hub reconcilieren, muessen
selbst genau einmal neu laden, falls `changed=True`.
"""
from typing import Any, Dict, List

from mcp.config import core_mcp_names, get_all_mcps
from mcp.installer_common import InstallationError, custom_mcp_dir, is_installer_owned
from mcp.installer_manifest import build_tool_intent_mirror
from mcp.installer_registry import MANAGED_BY_INSTALLER, remove_registry_entry, upsert_registry_entry


def reconcile_tool_manifest_mirrors() -> Dict[str, Any]:
    """Geht jeden installer-relevanten Registry-Eintrag durch und repariert
    Marker-Backfill, Mirror-Drift und verwaiste Eintraege. Liefert ein
    strukturiertes Ergebnis fuer den Aufrufer (Hub-Start, SP3 DECIDE 1)."""
    repaired: List[str] = []
    removed: List[str] = []
    unresolved: List[str] = []
    core_names = core_mcp_names()

    for name, entry in get_all_mcps().items():
        if name in core_names:
            continue
        _reconcile_entry(name, dict(entry), repaired, removed, unresolved)

    return {
        "changed": bool(repaired or removed),
        "repaired": repaired,
        "removed": removed,
        "unresolved": unresolved,
    }


def _reconcile_entry(
    name: str,
    entry: Dict[str, Any],
    repaired: List[str],
    removed: List[str],
    unresolved: List[str],
) -> None:
    """Eine Schreiboperation pro Eintrag und Lauf: Marker-Backfill und
    Mirror-Reparatur werden im selben `entry`-Dict gesammelt und zusammen
    ueber genau einen `upsert_registry_entry()`-Aufruf geschrieben."""
    has_marker = entry.get("managed_by") == MANAGED_BY_INSTALLER
    marker_backfilled = False
    if not has_marker:
        if not is_installer_owned(name):
            # Bundle und/oder Receipt fehlen, Marker fehlt - Eigentum nicht
            # beweisbar. Nicht raten, nicht loeschen (Codex DECIDE 2).
            unresolved.append(name)
            return
        entry["managed_by"] = MANAGED_BY_INSTALLER
        marker_backfilled = True

    if not custom_mcp_dir(name).exists():
        remove_registry_entry(name)
        removed.append(name)
        return

    mirror_changed, mirror_unresolved = _refresh_mirror(name, entry)
    if mirror_unresolved:
        # Codex Checkpoint 4 P1: ein invalides Bundle darf einen vorhandenen
        # Mirror nicht aktiv stehen lassen (Fail-closed statt stale). Der
        # `return` hier wuerde sonst auch einen im selben Lauf bereits
        # gesetzten Marker-Backfill verwerfen, ohne ihn zu schreiben -
        # deshalb laeuft der Schreib-Check unten weiter statt fruehzeitig
        # zurueckzukehren.
        unresolved.append(name)

    if marker_backfilled or mirror_changed:
        upsert_registry_entry(name, entry)
        repaired.append(name)


def _refresh_mirror(name: str, entry: Dict[str, Any]) -> tuple[bool, bool]:
    """Baut den Mirror frisch aus der Bundle-tool_intents.json (deckt sowohl
    fehlende als auch hash-abweichende Mirrors ab - beides ist derselbe Fix:
    der Registry-Mirror muss der aktuellen Bundle-Wahrheit entsprechen).
    Liefert `(changed, unresolved)`; schreibt selbst nichts in die Registry."""
    bundle_intents_path = custom_mcp_dir(name) / "tool_intents.json"
    if not bundle_intents_path.exists():
        if entry.get("tool_intents"):
            entry["tool_intents"] = None
            return True, False
        return False, False

    try:
        fresh_mirror = build_tool_intent_mirror(
            bundle_intents_path, bundle_version=str(entry.get("version", "") or "")
        )
    except InstallationError:
        # Bundle-tool_intents.json ist invalide (z.B. leer, kaputtes JSON,
        # fehlende Pflichtfelder) - kein sicherer Wiederaufbau moeglich.
        # Codex Checkpoint 4 P1: ein vorhandener alter Mirror darf trotzdem
        # nicht aktiv bleiben (Fail-closed, "Bundle = Authoring Source") -
        # er wird deaktiviert und die Aenderung gilt als `changed`, der
        # Eintrag bleibt zusaetzlich `unresolved`, bis das Bundle repariert
        # wird.
        if entry.get("tool_intents"):
            entry["tool_intents"] = None
            return True, True
        return False, True

    if entry.get("tool_intents") != fresh_mirror:
        entry["tool_intents"] = fresh_mirror
        return True, False
    return False, False
