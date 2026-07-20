import sqlite3
from datetime import datetime
from typing import Dict, Optional

from ..config import DB_PATH


def create_facts_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            subject TEXT,
            key TEXT,
            value TEXT,
            layer TEXT DEFAULT 'ltm',
            created_at TEXT
        )
        """
    )


def migrate_facts_table(conn: sqlite3.Connection) -> None:
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='facts'"
    ).fetchone()
    if not exists:
        create_facts_table(conn)


def insert_fact(
    conversation_id: str,
    subject: str,
    key: str,
    value: str,
    layer: str = "ltm",
) -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO facts
            (conversation_id, subject, key, value, layer, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id, subject, key, value, layer,
                datetime.utcnow().isoformat(timespec="seconds") + "Z",
            )
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def load_fact(conversation_id: str, key: str) -> Optional[str]:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT value FROM facts
            WHERE conversation_id = ? AND key = ?
            ORDER BY id DESC LIMIT 1
            """,
            (conversation_id, key)
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def row_to_fact_dict(row) -> Dict:
    return {
        "id": row[0],
        "conversation_id": row[1],
        "subject": row[2],
        "key": row[3],
        "value": row[4],
        "layer": row[5],
        "created_at": row[6],
    }
