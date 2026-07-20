import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from ..config import DB_PATH


def create_workspace_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            content TEXT NOT NULL,
            entry_type TEXT DEFAULT 'observation',
            source_layer TEXT DEFAULT 'thinking',
            created_at TEXT NOT NULL,
            updated_at TEXT,
            promoted BOOLEAN DEFAULT 0,
            promoted_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_workspace_conv ON workspace_entries(conversation_id)"
    )


def migrate_workspace_table(conn: sqlite3.Connection) -> None:
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='workspace_entries'"
    ).fetchone()
    if not exists:
        create_workspace_table(conn)


def save_workspace_entry(
    conversation_id: str,
    content: str,
    entry_type: str = "observation",
    source_layer: str = "thinking",
) -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO workspace_entries
            (conversation_id, content, entry_type, source_layer, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, content, entry_type, source_layer, now)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_workspace_entries(
    conversation_id: Optional[str] = None,
    limit: int = 50,
    entry_type: Optional[str] = None,
) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    try:
        conditions, params = [], []
        if conversation_id:
            conditions.append("conversation_id = ?")
            params.append(conversation_id)
        if entry_type:
            conditions.append("entry_type = ?")
            params.append(entry_type)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"""
            SELECT id, conversation_id, content, entry_type, source_layer,
                   created_at, updated_at, promoted, promoted_at
            FROM workspace_entries {where}
            ORDER BY id DESC LIMIT ?
            """,
            (*params, limit)
        ).fetchall()
        return [_row_to_workspace_entry(r) for r in rows]
    finally:
        conn.close()


def get_workspace_entry(entry_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            """
            SELECT id, conversation_id, content, entry_type, source_layer,
                   created_at, updated_at, promoted, promoted_at
            FROM workspace_entries WHERE id = ?
            """,
            (entry_id,)
        ).fetchone()
        return _row_to_workspace_entry(row) if row else None
    finally:
        conn.close()


def update_workspace_entry(entry_id: int, content: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    try:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        cur = conn.execute(
            "UPDATE workspace_entries SET content=?, updated_at=? WHERE id=?",
            (content, now, entry_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_workspace_entry(entry_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("DELETE FROM workspace_entries WHERE id=?", (entry_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_unpromoted_entries() -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT id, conversation_id, content, entry_type, source_layer,
                   created_at, updated_at, promoted, promoted_at
            FROM workspace_entries WHERE promoted = 0 ORDER BY id ASC
            """
        ).fetchall()
        return [_row_to_workspace_entry(r) for r in rows]
    finally:
        conn.close()


def mark_promoted(entry_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    try:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        cur = conn.execute(
            "UPDATE workspace_entries SET promoted=1, promoted_at=? WHERE id=?",
            (now, entry_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _row_to_workspace_entry(row) -> Dict:
    return {
        "id": row[0], "conversation_id": row[1], "content": row[2],
        "entry_type": row[3], "source_layer": row[4],
        "created_at": row[5], "updated_at": row[6],
        "promoted": bool(row[7]), "promoted_at": row[8],
    }
