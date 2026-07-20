import logging
import shutil
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from mcp.hub import get_hub
from mcp.installer_common import (
    InstallationError,
    MAX_SIZE,
    custom_mcps_dir,
    custom_mcp_dir,
    reload_hub_registry,
    run_post_install_health_check,
)
from mcp.installer_manifest import extract_archive
from mcp.installer_runtime import prepare_runtime
from mcp.installer_receipt import build_install_receipt, write_install_receipt
from mcp.installer_registry import remove_registry_entry, upsert_registry_entry
from mcp.config import get_all_mcps, get_registry_path

router = APIRouter()
_logger = logging.getLogger(__name__)


@router.post("/install", response_model=None)
async def install_mcp(request: Request, file: Any = None):
    target_dir = None
    try:
        upload = await _resolve_upload(file=file, request=request)
        content = await upload.read()
        if len(content) > MAX_SIZE:
            raise HTTPException(400, "File too large (max 50MB)")

        temp_extract, config = extract_archive(upload.filename, content)
        mcp_name = str(config["id"])
        target_dir = custom_mcp_dir(mcp_name)
        if target_dir.exists() or mcp_name in get_all_mcps():
            raise HTTPException(409, f"MCP '{mcp_name}' already exists")

        custom_mcps_dir().mkdir(parents=True, exist_ok=True)
        shutil.move(str(temp_extract), str(target_dir))
        runtime_state = prepare_runtime(target_dir, config)
        upsert_registry_entry(mcp_name, config)
        receipt = build_install_receipt(
            mcp_name,
            config,
            target_dir,
            get_registry_path(),
            runtime_kind=runtime_state["runtime_kind"],
            runtime_created_paths=runtime_state["runtime_created_paths"],
        )
        write_install_receipt(target_dir, receipt)

        hub = get_hub()
        reload_method = reload_hub_registry(hub)
        health = await run_post_install_health_check(hub, mcp_name)
        if health.get("status") == "unhealthy":
            raise InstallationError(
                f"Health check failed for MCP '{mcp_name}': {health.get('reason')}",
                target_dir,
            )
        return _success_payload(mcp_name, config, health, reload_method)
    except InstallationError as exc:
        _cleanup_failed_install(locals().get("mcp_name"), exc.target_dir)
        status_code = 400 if exc.target_dir is None else 500
        raise HTTPException(status_code, exc.message) from exc
    except HTTPException:
        raise
    except Exception as exc:
        _cleanup_failed_install(locals().get("mcp_name"), target_dir)
        raise HTTPException(500, f"Installation failed: {exc}") from exc


async def _resolve_upload(file: Any, request: Request | None) -> Any:
    if file is not None:
        return file
    if request is None:
        raise HTTPException(400, "No file upload provided")
    content_type = str(request.headers.get("content-type", "")).lower()
    if "multipart/form-data" in content_type:
        try:
            form = await request.form()
        except Exception as exc:
            raise HTTPException(
                400,
                "Multipart upload requires python-multipart at runtime",
            ) from exc
        upload = form.get("file")
        if upload is None:
            raise HTTPException(400, "No file upload provided")
        return upload
    body = await request.body()
    if not body:
        raise HTTPException(400, "No file upload provided")
    return _BodyUpload(body)

def _success_payload(
    mcp_name: str,
    config: Dict[str, Any],
    health: Dict[str, str],
    reload_method: str,
) -> Dict[str, Any]:
    return {
        "success": True,
        "mcp": {
            "name": mcp_name,
            "display_name": config.get("display_name", mcp_name),
            "version": config.get("version", ""),
            "description": config.get("description", ""),
            "url": config.get("url"),
        },
        "health": {**health, "reload_method": reload_method},
    }


def _cleanup_failed_install(mcp_name: str | None, target_dir: Path | None) -> Dict[str, bool]:
    """Reihenfolge bindend, identisch zu installer_manage_routes.delete_mcp()
    (SP3 Lifecycle-Invariante): Mirror entfernen -> Hub reload -> Bundle
    entfernen. Ohne den zweiten Reload haelt der Hub nach einem fehl-
    geschlagenen Healthcheck weiterhin den bereits wieder entfernten
    Registry-Eintrag im Speicher (er wurde vor dem Healthcheck einmal
    geladen, siehe reload_hub_registry()-Aufruf oben in install_mcp()).

    Die drei Stufen sind ABHAENGIG, nicht unabhaengig (Codex Checkpoint 4 P1,
    3. Runde - widerruft die 2. Runde: "jede Stufe einzeln absichern" hatte
    einen Registry-Fehler nur geloggt und trotzdem Hub-Reload UND
    Bundle-Loeschung ausgefuehrt. Das erzeugt genau die verbotenen Zustaende:
    Registry zeigt noch auf ein bereits geloeschtes Bundle, oder der
    Hub-Cache zeigt auf ein bereits geloeschtes Bundle, falls der Reload
    selbst fehlschlaegt). Scheitert eine Stufe, wird geloggt, das Bundle
    bleibt erhalten, und die Funktion stoppt - nur wenn Registry-Entfernung
    UND Hub-Reload beide erfolgreich waren (oder gar kein mcp_name vorlag,
    also diese beiden Stufen nie zutrafen), wird das Bundle geloescht. Diese
    Funktion wirft selbst nie (Best-Effort-Rollback nach einem bereits
    fehlgeschlagenen Install - ein Crash hier wuerde den eigentlichen, dem
    Nutzer gemeldeten Install-/Healthcheck-Fehler verdecken). Der
    Rueckgabewert ist ein strukturierter Status pro Stufe (fuer Tests/
    Diagnose, kein Vertrag fuer Aufrufer - die bisherigen Aufrufer ignorieren
    ihn unveraendert)."""
    status = {"registry_removed": False, "hub_reloaded": False, "bundle_removed": False}
    if mcp_name:
        try:
            remove_registry_entry(mcp_name)
            status["registry_removed"] = True
        except Exception:
            _logger.exception("Failed to remove registry entry during rollback: %s", mcp_name)
            return status
        try:
            reload_hub_registry(get_hub())
            status["hub_reloaded"] = True
        except Exception:
            _logger.exception("Failed to reload hub registry during rollback: %s", mcp_name)
            return status
    if target_dir:
        if target_dir.exists():
            try:
                shutil.rmtree(target_dir)
            except Exception:
                _logger.exception("Failed to remove MCP bundle directory after rollback: %s", target_dir)
            if target_dir.exists():
                _logger.error("MCP bundle directory still exists after rollback cleanup: %s", target_dir)
        if not target_dir.exists():
            status["bundle_removed"] = True
    return status


class _BodyUpload:
    filename = "mcp_upload.zip"

    def __init__(self, payload: bytes):
        self._payload = payload

    async def read(self) -> bytes:
        return self._payload
