from container_commander_v2_fakes import _init_blueprint_db

from blueprint_store import get_blueprint, list_blueprints  # noqa: E402
from blueprint_write import create_blueprint, delete_blueprint, export_blueprint_yaml, import_blueprint_yaml, update_blueprint  # noqa: E402


def test_blueprint_views_use_v2_shape(monkeypatch, tmp_path):
    db_path = tmp_path / "commander.db"
    _init_blueprint_db(db_path)
    monkeypatch.setenv("COMMANDER_DB_PATH", str(db_path))

    import blueprint_store  # noqa: E402

    blueprint_store.DB_PATH = str(db_path)

    listed = list_blueprints()
    assert listed == {
        "blueprints": [
            {
                "blueprint_id": "demo",
                "name": "Demo",
                "description": "Example blueprint",
                "version": "2026-05-15T11:00:00Z",
            }
        ]
    }

    detail = get_blueprint("demo")
    assert detail["blueprint"]["blueprint_id"] == "demo"
    assert detail["blueprint"]["definition"]["dockerfile"] == "FROM python:3.12"
    assert detail["blueprint"]["definition"]["image"] == "python:3.12"


def test_blueprint_write_roundtrip_uses_v2_store(monkeypatch, tmp_path):
    db_path = tmp_path / "commander.db"
    monkeypatch.setenv("COMMANDER_DB_PATH", str(db_path))

    import blueprint_store  # noqa: E402
    import blueprint_store_db  # noqa: E402
    import blueprint_write  # noqa: E402

    blueprint_store.DB_PATH = str(db_path)
    blueprint_store_db.DB_PATH = str(db_path)
    blueprint_write.get_conn.__globals__["DB_PATH"] = str(db_path)

    created = create_blueprint(
        {
            "id": "writer",
            "name": "Writer",
            "description": "Write path",
            "dockerfile": "FROM python:3.12",
            "tags": ["gpu"],
        }
    )
    assert created["created"] is True
    assert created["blueprint"]["blueprint_id"] == "writer"

    updated = update_blueprint("writer", {"description": "Updated", "tags": ["cpu"]})
    assert updated["updated"] is True
    assert updated["blueprint"]["definition"]["description"] == "Updated"
    assert updated["blueprint"]["definition"]["tags"] == ["cpu"]

    exported = export_blueprint_yaml("writer")
    assert "yaml" in exported
    assert "Writer" in exported["yaml"]

    imported = import_blueprint_yaml(
        """
id: imported
name: Imported
description: Imported blueprint
dockerfile: FROM alpine:3.20
"""
    )
    assert imported["created"] is True
    assert imported["blueprint"]["blueprint_id"] == "imported"

    deleted = delete_blueprint("writer")
    assert deleted == {"deleted": True, "blueprint_id": "writer"}
