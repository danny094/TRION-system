"""
mcp.installer_paths
=====================
Pfadaufloesung und -validierung fuer installer-verwaltete MCP-Bundles unter
custom_mcps/.

Herausgeloest aus mcp/installer_common.py (Codex Checkpoint 4 P0, 2. Runde:
die neue zentrale MCP-ID-Validierung plus die defensive custom_mcp_dir()-
Pruefung haetten installer_common.py ueber Doc 07s 200-Zeilen-Grenze
geschoben). `installer_common.py` re-exportiert alle Namen hier, damit kein
bestehender Call-Site-Import (installer_install_routes.py,
installer_manage_routes.py, installer_manage_config.py,
installer_reconcile.py, Tests) geaendert werden muss - gleiches Vorgehen wie
beim SP0-Split von installer_manifest.py.
"""
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException
from config import get_custom_mcps_dir

from mcp.installer_receipt import RECEIPT_FILE


def validate_mcp_id(name: str) -> str:
    """Zentrale Pruefung (Codex Checkpoint 4 P0, 2. Runde): eine MCP-ID muss
    ein einzelnes, sicheres Pfadsegment sein. Ohne diese Pruefung konnte eine
    ID wie '../victim' aus custom_mcps/ ausbrechen - sowohl bei der
    Installation (target_dir wird in installer_install_routes.py direkt aus
    der Manifest-ID gebaut, bevor irgendein Receipt existiert) als auch bei
    jedem spaeteren Zugriff ueber custom_mcp_dir() (delete/toggle/config/
    icon-Routen in installer_manage_routes.py). Jede dieser Stellen ruft
    custom_mcp_dir() auf - eine Pruefung hier deckt sie alle ab, eine zweite
    Pruefung z.B. in installer_manifest_normalize.py waere eine doppelte,
    nicht konsolidierte Implementierung derselben Verantwortung (Doc 36
    Regel 1)."""
    candidate = str(name)
    if (
        not candidate
        or candidate in {".", ".."}
        or "/" in candidate
        or "\\" in candidate
        or "\x00" in candidate
        or Path(candidate).is_absolute()
        or Path(candidate).name != candidate
    ):
        raise HTTPException(400, f"Invalid MCP id: {name!r}")
    return candidate


def custom_mcps_dir() -> Path:
    return Path(get_custom_mcps_dir())


def custom_mcp_dir(name: str) -> Path:
    """Loest die MCP-ID zu einem Verzeichnis unter custom_mcps/ auf.
    `validate_mcp_id()` prueft das Pfadsegment selbst; die anschliessende
    `candidate.parent != root`-Pruefung beweist defensiv, dass der
    AUFGELOESTE Zielpfad auch wirklich direkt unter custom_mcps/ liegt -
    zweite, unabhaengige Sicherung fuer den Fall, dass eine zukuenftige
    Aenderung an validate_mcp_id() eine Luecke uebersieht (Codex Checkpoint
    4 P0, 2. Runde: 'custom_mcp_dir() sollte defensiv beweisen, dass der
    aufgeloeste Zielpfad direkt unter custom_mcps/ liegt')."""
    safe_name = validate_mcp_id(name)
    root = custom_mcps_dir().resolve()
    candidate = (root / safe_name).resolve()
    if candidate.parent != root:
        raise HTTPException(400, f"Invalid MCP id: {name!r}")
    return candidate


def custom_config_path(name: str) -> Path:
    target = custom_mcp_dir(name)
    mcp_manifest = target / "mcp.json"
    if mcp_manifest.exists():
        return mcp_manifest
    return target / "config.json"


def receipt_path(name: str) -> Path:
    return custom_mcp_dir(name) / RECEIPT_FILE


def is_installer_owned(name: str) -> bool:
    target = custom_mcp_dir(name)
    return target.exists() and receipt_path(name).exists()


def resolve_icon_path(name: str, config: Dict[str, Any]) -> Path | None:
    """Codex Checkpoint 4 P0 (3. Runde): `str(candidate).startswith(str(root))`
    ist KEINE Pfad-, sondern eine String-Pruefung - 'custom/demo-secrets'
    beginnt als Zeichenkette mit 'custom/demo' und waere damit faelschlich
    als 'innerhalb des Bundles' akzeptiert worden, obwohl es ein voellig
    anderes, nur namensaehnliches Nachbarverzeichnis ist. Die Pruefung muss
    die echte Pfadbeziehung pruefen: `candidate == root` (Icon direkt im
    Bundle-Wurzelverzeichnis) oder `root in candidate.parents` (Icon in einem
    Unterverzeichnis des Bundles)."""
    ui = config.get("ui")
    if not isinstance(ui, dict):
        return None
    icon_rel = ui.get("icon")
    if not isinstance(icon_rel, str) or not icon_rel.strip():
        return None
    candidate = (custom_mcp_dir(name) / icon_rel).resolve()
    root = custom_mcp_dir(name).resolve()
    if not (candidate == root or root in candidate.parents) or not candidate.exists():
        return None
    return candidate
