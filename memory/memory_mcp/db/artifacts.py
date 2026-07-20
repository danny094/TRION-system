import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from ..config import DB_PATH


def create_artifacts_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trion_artifact_registry (
            id          TEXT PRIMARY KEY,
            type        TEXT NOT NULL,
            name        TEXT NOT NULL,
            purpose     TEXT,
            related_secrets TEXT,
            depends_on  TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT,
            status      TEXT NOT NULL DEFAULT 'active',
            meta        TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifact_type   ON trion_artifact_registry(type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifact_name   ON trion_artifact_registry(name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifact_status ON trion_artifact_registry(status)")


def migrate_artifacts_table(conn: sqlite3.Connection) -> None:
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='trion_artifact_registry'"
    ).fetchone()
    if not exists:
        create_artifacts_table(conn)


def _artifact_id(type: str, name: str) -> str:
    return f"{str(type).strip().lower()}-{str(name).strip().lower()}"


def artifact_save(
    type: str,
    name: str,
    purpose: Optional[str] = None,
    related_secrets: Optional[str] = None,
    depends_on: Optional[str] = None,
    meta: Optional[str] = None,
    artifact_id: Optional[str] = None,
) -> str:
    aid = artifact_id or _artifact_id(type, name)
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    conn = sqlite3.connect(DB_PATH)
    try:
        existing = conn.execute(
            "SELECT id FROM trion_artifact_registry WHERE id = ?", (aid,)
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE trion_artifact_registry
                SET type=?, name=?, purpose=?, related_secrets=?,
                    depends_on=?, meta=?, updated_at=?
                WHERE id=?
                """,
                (type, name, purpose, related_secrets, depends_on, meta, now, aid),
            )
        else:
            conn.execute(
                """
                INSERT INTO trion_artifact_registry
                (id, type, name, purpose, related_secrets, depends_on,
                 created_at, updated_at, status, meta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
                """,
                (aid, type, name, purpose, related_secrets, depends_on, now, now, meta),
            )
        conn.commit()
        return aid
    finally:
        conn.close()


def artifact_get(name: str) -> Optional[Dict]:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            """
            SELECT id, type, name, purpose, related_secrets, depends_on,
                   created_at, updated_at, status, meta
            FROM trion_artifact_registry
            WHERE name = ? ORDER BY created_at DESC LIMIT 1
            """,
            (name,),
        ).fetchone()
        return _row_to_artifact(row) if row else None
    finally:
        conn.close()


def artifact_list(
    type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    try:
        conditions: List[str] = []
        params: List[str] = []
        if type:
            conditions.append("type = ?")
            params.append(type)
        if status:
            conditions.append("status = ?")
            params.append(status)
        else:
            conditions.append("status != 'removed'")
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        rows = conn.execute(
            f"""
            SELECT id, type, name, purpose, related_secrets, depends_on,
                   created_at, updated_at, status, meta
            FROM trion_artifact_registry {where}
            ORDER BY created_at DESC LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        return [_row_to_artifact(r) for r in rows]
    finally:
        conn.close()


def artifact_update(name: str, status: Optional[str] = None, meta: Optional[str] = None) -> bool:
    conn = sqlite3.connect(DB_PATH)
    try:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        sets: List[str] = ["updated_at = ?"]
        params: List = [now]
        if status is not None:
            sets.append("status = ?")
            params.append(status)
        if meta is not None:
            sets.append("meta = ?")
            params.append(meta)
        params.append(name)
        cur = conn.execute(
            f"UPDATE trion_artifact_registry SET {', '.join(sets)} WHERE name = ?",
            params,
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _row_to_artifact(row) -> Dict:
    return {
        "id": row[0], "type": row[1], "name": row[2], "purpose": row[3],
        "related_secrets": row[4], "depends_on": row[5],
        "created_at": row[6], "updated_at": row[7],
        "status": row[8], "meta": row[9],
    }
