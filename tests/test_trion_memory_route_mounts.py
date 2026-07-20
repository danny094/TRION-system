from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def test_trion_memory_routes_are_only_mounted_under_trion_memory_prefix():
    main_source = (ADMIN_API_DIR / "main.py").read_text(encoding="utf-8")
    commander_source = (ADMIN_API_DIR / "commander_routes.py").read_text(encoding="utf-8")

    assert "app.include_router(memory_router)" not in main_source
    assert 'router.include_router(trion_memory_router, prefix="/trion/memory")' in commander_source

    trion_memory_source = (ADMIN_API_DIR / "trion_memory_routes.py").read_text(encoding="utf-8")
    assert '@router.post("/remember")' in trion_memory_source
    assert '@router.get("/recent")' in trion_memory_source
    assert '@router.get("/recall")' in trion_memory_source
    assert '@router.get("/status")' in trion_memory_source
    assert "not part of the WebUI memory app" in trion_memory_source or "nicht" in trion_memory_source
    assert "identity_path" in trion_memory_source
    assert "conversation_meta" in trion_memory_source
    assert "container_commander.home_memory" not in trion_memory_source
    assert "from home_note_memory import" in trion_memory_source
