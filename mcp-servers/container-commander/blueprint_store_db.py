from __future__ import annotations

import os
import sqlite3


def _db_path() -> str:
    return os.environ.get("COMMANDER_DB_PATH", "/app/data/commander.db")


def get_conn() -> sqlite3.Connection:
    db_path = _db_path()
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_store_initialized() -> None:
    conn = get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blueprints (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                extends TEXT,
                dockerfile TEXT DEFAULT '',
                image TEXT,
                image_digest TEXT,
                system_prompt TEXT DEFAULT '',
                resources_json TEXT DEFAULT '{}',
                secrets_json TEXT DEFAULT '[]',
                mounts_json TEXT DEFAULT '[]',
                storage_scope TEXT DEFAULT '',
                ports_json TEXT DEFAULT '[]',
                runtime TEXT DEFAULT '',
                devices_json TEXT DEFAULT '[]',
                hardware_intents_json TEXT DEFAULT '[]',
                environment_json TEXT DEFAULT '{}',
                healthcheck_json TEXT DEFAULT '{}',
                pre_start_exec_json TEXT DEFAULT '{}',
                cap_add_json TEXT DEFAULT '[]',
                security_opt_json TEXT DEFAULT '[]',
                cap_drop_json TEXT DEFAULT '[]',
                privileged INTEGER DEFAULT 0,
                read_only_rootfs INTEGER DEFAULT 0,
                shm_size TEXT DEFAULT '',
                ipc_mode TEXT DEFAULT '',
                network TEXT DEFAULT 'internal',
                tags_json TEXT DEFAULT '[]',
                exec_policy_json TEXT DEFAULT '[]',
                icon TEXT DEFAULT '📦',
                created_at TEXT,
                updated_at TEXT,
                is_deleted INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
