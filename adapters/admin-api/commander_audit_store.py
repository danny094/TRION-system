from __future__ import annotations

import os
import sqlite3
from typing import Optional


def _db_path() -> str:
    return os.environ.get("COMMANDER_DB_PATH", "/app/data/commander.db")


def _get_conn() -> sqlite3.Connection:
    db_path = _db_path()
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_audit_log_initialized() -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS container_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                container_id TEXT,
                blueprint_id TEXT,
                action TEXT,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def log_action(container_id: str, blueprint_id: str, action: str, details: str = "") -> None:
    ensure_audit_log_initialized()
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO container_log (container_id, blueprint_id, action, details) VALUES (?, ?, ?, ?)",
            (container_id, blueprint_id, action, details),
        )
        conn.commit()
    finally:
        conn.close()


def get_audit_log(blueprint_id: Optional[str] = None, limit: int = 50) -> list[dict]:
    ensure_audit_log_initialized()
    safe_limit = max(1, int(limit))
    conn = _get_conn()
    try:
        if blueprint_id:
            rows = conn.execute(
                "SELECT * FROM container_log WHERE blueprint_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
                (blueprint_id, safe_limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM container_log ORDER BY created_at DESC, id DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
