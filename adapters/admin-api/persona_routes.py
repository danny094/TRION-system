from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from core.persona import (
    list_personas,
    load_persona,
    save_persona,
    delete_persona,
    switch_persona,
    get_active_persona_name,
    PERSONAS_DIR
)
from utils.logger import log_info, log_error, log_warn


router = APIRouter(
    prefix="/api/personas",
    tags=["personas"],
    responses={
        404: {"description": "Persona not found"},
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"}
    }
)


def _validate_persona_name(name: str) -> bool:
    if not name or len(name) > 50:
        return False
    if ".." in name or "/" in name or "\\" in name:
        return False
    if not name.replace("-", "").replace("_", "").isalnum():
        return False
    return True


def _validate_persona_content(content: str) -> tuple[bool, Optional[str]]:
    if len(content) > 10 * 1024:
        return False, "Content too large (max 10KB)"
    if "[IDENTITY]" not in content:
        return False, "Missing required [IDENTITY] section"
    if "name:" not in content.lower():
        return False, "Missing 'name' field in [IDENTITY]"
    return True, None


@router.get("/")
async def get_all_personas() -> Dict[str, Any]:
    try:
        personas = list_personas()
        active = get_active_persona_name()
        log_info(f"[PersonaAPI] Listed {len(personas)} personas, active: {active}")
        return {"personas": personas, "active": active, "count": len(personas)}
    except Exception as e:
        log_error(f"[PersonaAPI] Error listing personas: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list personas: {str(e)}")


@router.get("/{name}")
async def get_persona_by_name(name: str) -> Dict[str, Any]:
    if not _validate_persona_name(name):
        raise HTTPException(status_code=400, detail="Invalid persona name. Use alphanumeric, dash, underscore only.")
    try:
        persona_file = PERSONAS_DIR / f"{name}.txt"
        if not persona_file.exists():
            raise HTTPException(status_code=404, detail=f"Persona '{name}' not found")
        content = persona_file.read_text(encoding="utf-8")
        active = get_active_persona_name()
        return {"name": name, "content": content, "exists": True, "size": len(content), "active": (name == active)}
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[PersonaAPI] Error getting persona {name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get persona: {str(e)}")


@router.post("/")
async def upload_persona(file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        if not file.filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail="Only .txt files are allowed")
        name = file.filename[:-4]
        if not _validate_persona_name(name):
            raise HTTPException(status_code=400, detail="Invalid filename. Use alphanumeric, dash, underscore only.")
        content = await file.read()
        content_str = content.decode('utf-8')
        is_valid, error_msg = _validate_persona_content(content_str)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid persona content: {error_msg}")
        success = save_persona(name, content_str)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save persona file")
        log_info(f"[PersonaAPI] Uploaded persona: {name} ({len(content_str)} bytes)")
        return {"success": True, "name": name, "size": len(content_str), "message": f"Persona '{name}' uploaded successfully"}
    except HTTPException:
        raise
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")
    except Exception as e:
        log_error(f"[PersonaAPI] Error uploading persona: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload persona: {str(e)}")


@router.put("/content/{name}")
async def update_persona(name: str, payload: Dict[str, str]) -> Dict[str, Any]:
    if not _validate_persona_name(name):
        raise HTTPException(status_code=400, detail="Invalid persona name")
    content = str((payload or {}).get("content") or "")
    is_valid, error_msg = _validate_persona_content(content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid persona content: {error_msg}")
    try:
        success = save_persona(name, content)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update persona")
        active = get_active_persona_name()
        log_info(f"[PersonaAPI] Updated persona: {name}")
        return {"success": True, "name": name, "active": active == name, "size": len(content)}
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[PersonaAPI] Error updating persona {name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update persona: {str(e)}")


@router.put("/switch")
async def switch_active_persona(name: str) -> Dict[str, Any]:
    if not _validate_persona_name(name):
        raise HTTPException(status_code=400, detail="Invalid persona name")
    try:
        persona_file = PERSONAS_DIR / f"{name}.txt"
        if not persona_file.exists():
            raise HTTPException(status_code=404, detail=f"Persona '{name}' not found")
        previous = get_active_persona_name()
        persona = switch_persona(name)
        log_info(f"[PersonaAPI] Switched persona: {previous} → {name}")
        return {"success": True, "previous": previous, "current": name, "message": f"Switched to '{name}'", "persona_name": persona.name}
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[PersonaAPI] Error switching persona: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to switch persona: {str(e)}")


@router.delete("/{name}")
async def delete_persona_endpoint(name: str) -> Dict[str, Any]:
    if not _validate_persona_name(name):
        raise HTTPException(status_code=400, detail="Invalid persona name")
    if name == "default":
        raise HTTPException(status_code=400, detail="Cannot delete 'default' persona (protected)")
    try:
        persona_file = PERSONAS_DIR / f"{name}.txt"
        if not persona_file.exists():
            raise HTTPException(status_code=404, detail=f"Persona '{name}' not found")
        success = delete_persona(name)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete persona")
        log_info(f"[PersonaAPI] Deleted persona: {name}")
        return {"success": True, "deleted": name, "message": f"Persona '{name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[PersonaAPI] Error deleting persona: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete persona: {str(e)}")
