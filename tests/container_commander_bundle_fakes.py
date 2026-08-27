from pathlib import Path
import sqlite3
import sys


BUNDLE_DIR = Path(__file__).resolve().parents[1] / "examples" / "container_commander_bundle"
if str(BUNDLE_DIR) not in sys.path:
    sys.path.insert(0, str(BUNDLE_DIR))


def _init_blueprint_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE blueprints (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                dockerfile TEXT DEFAULT '',
                image TEXT DEFAULT '',
                runtime TEXT DEFAULT '',
                ports_json TEXT DEFAULT '[]',
                mounts_json TEXT DEFAULT '[]',
                environment_json TEXT DEFAULT '{}',
                resources_json TEXT DEFAULT '{}',
                tags_json TEXT DEFAULT '[]',
                icon TEXT DEFAULT '📦',
                created_at TEXT,
                updated_at TEXT,
                is_deleted INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            INSERT INTO blueprints (
                id, name, description, dockerfile, image, runtime, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "demo",
                "Demo",
                "Example blueprint",
                "FROM python:3.12",
                "python:3.12",
                "docker",
                "2026-05-15T10:00:00Z",
                "2026-05-15T11:00:00Z",
            ),
        )
        conn.commit()
    finally:
        conn.close()
