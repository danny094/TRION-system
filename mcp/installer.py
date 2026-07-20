from fastapi import APIRouter

from mcp.installer_install_routes import router as install_router
from mcp.installer_manage_routes import router as manage_router

router = APIRouter()
router.include_router(install_router)
router.include_router(manage_router)
