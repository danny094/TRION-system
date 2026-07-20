import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from ..config import DB_PATH


def create_skill_metrics_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id TEXT UNIQUE NOT NULL,
            version TEXT DEFAULT '1.0',
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            avg_exec_time_ms REAL DEFAULT 0,
            last_error TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            updated_at TEXT
        )
        """
    )


def migrate_skill_metrics_table(conn: sqlite3.Connection) -> None:
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='skill_metrics'"
    ).fetchone()
    if not exists:
        create_skill_metrics_table(conn)


def upsert_skill_metric(
    skill_id: str,
    success: bool,
    exec_time_ms: float,
    error: Optional[str] = None,
    version: str = "1.0",
) -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        cur.execute(
            "SELECT id, success_count, failure_count, avg_exec_time_ms FROM skill_metrics WHERE skill_id = ?",
            (skill_id,)
        )
        row = cur.fetchone()
        if row:
            old_id, s_count, f_count, avg_time = row
            total = s_count + f_count
            new_avg = ((avg_time * total) + exec_time_ms) / (total + 1) if total > 0 else exec_time_ms
            if success:
                cur.execute(
                    "UPDATE skill_metrics SET success_count=success_count+1, avg_exec_time_ms=?, version=?, updated_at=? WHERE skill_id=?",
                    (new_avg, version, now, skill_id)
                )
            else:
                cur.execute(
                    "UPDATE skill_metrics SET failure_count=failure_count+1, avg_exec_time_ms=?, last_error=?, version=?, updated_at=? WHERE skill_id=?",
                    (new_avg, error, version, now, skill_id)
                )
            conn.commit()
            return old_id
        else:
            cur.execute(
                """INSERT INTO skill_metrics
                   (skill_id, version, success_count, failure_count, avg_exec_time_ms, last_error, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
                (skill_id, version, 1 if success else 0, 0 if success else 1, exec_time_ms, error, now, now)
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()


def get_skill_metric(skill_id: str) -> Optional[Dict]:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT * FROM skill_metrics WHERE skill_id = ?", (skill_id,)).fetchone()
        return _row_to_skill_metric(row) if row else None
    finally:
        conn.close()


def list_skill_metrics(status: Optional[str] = None, limit: int = 50) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM skill_metrics WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM skill_metrics ORDER BY updated_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [_row_to_skill_metric(r) for r in rows]
    finally:
        conn.close()


def update_skill_status(skill_id: str, status: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    try:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        cur = conn.execute(
            "UPDATE skill_metrics SET status=?, updated_at=? WHERE skill_id=?",
            (status, now, skill_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _row_to_skill_metric(row) -> Dict:
    return {
        "id": row[0], "skill_id": row[1], "version": row[2],
        "success_count": row[3], "failure_count": row[4],
        "avg_exec_time_ms": row[5], "last_error": row[6],
        "status": row[7], "created_at": row[8], "updated_at": row[9],
    }
