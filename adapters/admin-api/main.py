"""
TRION Admin API — Entry Point

Nur Verdrahtung. Keine Logik.
Start: uvicorn adapters.admin-api.main:app --port 8200
"""
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────

app = FastAPI(
    title="TRION Admin API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────

from settings_routes import router as settings_router
from provider_keys_routes import router as provider_keys_router
from commander_routes import router as commander_router
from secrets_routes import router as secrets_router
from vault_routes import router as vault_router
from protocol_routes import router as protocol_router
from runtime_routes import router as runtime_router
from storage_broker_routes import router as storage_broker_router
from runtime_hardware_routes import router as runtime_hardware_router
from workspace_routes import router as workspace_router
from chat_routes import router as chat_router
from models_routes import router as models_router
from tools_routes import router as tools_router
from mcp.installer import router as mcp_installer_router
from mcp.endpoint import router as mcp_hub_router
from persona_routes import router as persona_router
from maintenance_routes import router as maintenance_router
from autonomy_tool_policy_routes import router as autonomy_tool_policy_router
from autonomy_profile_routes import router as autonomy_profile_router
from tasks_routes import router as tasks_router
from plugins_routes import router as plugins_router
from memory_routes import router as memory_app_router
from memory_defaults_routes import router as memory_defaults_router

app.include_router(settings_router)
app.include_router(provider_keys_router)
app.include_router(commander_router)
app.include_router(secrets_router)
app.include_router(vault_router)
app.include_router(protocol_router)
app.include_router(runtime_router)
app.include_router(storage_broker_router)
app.include_router(runtime_hardware_router)
app.include_router(workspace_router)
app.include_router(chat_router)
app.include_router(models_router)
app.include_router(tools_router)
app.include_router(mcp_installer_router, prefix="/api/mcp")
app.include_router(mcp_hub_router)
app.include_router(persona_router)
app.include_router(maintenance_router)
app.include_router(autonomy_tool_policy_router)
app.include_router(autonomy_profile_router)
app.include_router(tasks_router)
app.include_router(plugins_router)
app.include_router(memory_app_router)
app.include_router(memory_defaults_router)


# ── Health & Root ──────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "trion-admin-api", "version": "2.0.0"}


@app.get("/")
async def root():
    return {
        "service": "TRION Admin API",
        "version": "2.0.0",
        "docs": "/docs",
        "endpoints": {
            "chat": "/api/chat",
            "models": "/api/models/catalog",
            "tags": "/api/tags",
            "tools": "/api/tools",
            "tasks": "/api/tasks/{task_id}/approve",
            "workspace": "/api/workspace",
            "mcp": "/mcp",
        },
    }


# ── Startup / Shutdown ─────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info("TRION Admin API starting...")

    async def _init_commander_store():
        try:
            from commander_deploy_blueprints import ensure_store_initialized
            await asyncio.to_thread(ensure_store_initialized)
            logger.info("[Startup] Commander store initialized")
        except Exception as e:
            logger.warning(f"[Startup] Commander store init failed (non-critical): {e}")

    async def _recover_containers():
        try:
            from commander_deploy_runtime_state import recover
            result = await asyncio.to_thread(recover)
            logger.info(f"[Startup] Container recovery: {result}")
        except Exception as e:
            logger.warning(f"[Startup] Container recovery failed (non-critical): {e}")

    async def _sync_blueprints():
        try:
            from commander_blueprint_graph_sync import sync_blueprints_to_graph
            count = await asyncio.to_thread(sync_blueprints_to_graph)
            logger.info(f"[Startup] {count} blueprints synced to graph")
        except Exception as e:
            logger.warning(f"[Startup] Blueprint graph sync failed (non-critical): {e}")

    asyncio.create_task(_init_commander_store())
    asyncio.create_task(_recover_containers())
    asyncio.create_task(_sync_blueprints())
    logger.info("TRION Admin API ready.")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("TRION Admin API shutting down.")
