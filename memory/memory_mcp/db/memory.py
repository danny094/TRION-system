import sqlite3
from datetime import datetime
from typing import Dict, Optional

from ..config import DB_PATH


def _ensure_memory_fts(conn: sqlite3.Connection, force_repair: bool = False) -> None:
    """
    Ensures memory_fts/triggers exist and are compatible with current schema.
    Repairs broken legacy states that trigger:
      DatabaseError: vtable constructor failed: memory_fts
    """
    cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(memory)").fetchall()}
    if not {"id", "content"}.issubset(cols):
        return

    fts_cols = ["content"]
    for c in ("conversation_id", "role", "tags", "layer", "created_at"):
        if c in cols:
            fts_cols.append(c)

    if not force_repair:
        try:
            conn.execute("SELECT rowid FROM memory_fts LIMIT 1").fetchall()
            return
        except sqlite3.DatabaseError:
            force_repair = True

    if not force_repair:
        return

    def _force_remove_broken_fts() -> None:
        conn.execute("PRAGMA writable_schema=ON")
        conn.execute("DELETE FROM sqlite_master WHERE name LIKE 'memory_fts%'")
        conn.execute(
            "DELETE FROM sqlite_master WHERE type='trigger' "
            "AND name IN ('memory_ai','memory_au','memory_ad')"
        )
        current_ver = conn.execute("PRAGMA schema_version").fetchone()[0]
        conn.execute(f"PRAGMA schema_version={int(current_ver) + 1}")
        conn.execute("PRAGMA writable_schema=OFF")

    trigger_cols = ", ".join(fts_cols)
    trigger_vals = ", ".join(f"new.{c}" for c in fts_cols)
    trigger_updates = ", ".join(f"{c}=new.{c}" for c in fts_cols)
    select_cols = ", ".join(fts_cols)

    conn.execute("DROP TRIGGER IF EXISTS memory_ai")
    conn.execute("DROP TRIGGER IF EXISTS memory_au")
    conn.execute("DROP TRIGGER IF EXISTS memory_ad")
    try:
        conn.execute("DROP TABLE IF EXISTS memory_fts")
    except sqlite3.DatabaseError as e:
        if "memory_fts" not in str(e).lower():
            raise
        _force_remove_broken_fts()
    _force_remove_broken_fts()

    conn.execute(
        f"""
        CREATE VIRTUAL TABLE memory_fts USING fts5(
            {", ".join(fts_cols)},
            content='memory',
            content_rowid='id'
        )
        """
    )
    conn.execute(
        f"""
        CREATE TRIGGER memory_ai AFTER INSERT ON memory BEGIN
            INSERT INTO memory_fts(rowid, {trigger_cols})
            VALUES (new.id, {trigger_vals});
        END;
        """
    )
    conn.execute(
        f"""
        CREATE TRIGGER memory_au AFTER UPDATE ON memory BEGIN
            UPDATE memory_fts
            SET {trigger_updates}
            WHERE rowid=new.id;
        END;
        """
    )
    conn.execute(
        """
        CREATE TRIGGER memory_ad AFTER DELETE ON memory BEGIN
            DELETE FROM memory_fts WHERE rowid=old.id;
        END;
        """
    )
    conn.execute(
        f"""
        INSERT INTO memory_fts(rowid, {trigger_cols})
        SELECT id, {select_cols}
        FROM memory
        """
    )


def create_memory_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            role TEXT,
            content TEXT,
            tags TEXT,
            layer TEXT DEFAULT 'auto',
            created_at TEXT
        )
        """
    )
    _ensure_memory_fts(conn, force_repair=False)


def migrate_memory_table(conn: sqlite3.Connection) -> None:
    columns = [row[1] for row in conn.execute("PRAGMA table_info(memory)").fetchall()]
    if "layer" not in columns:
        conn.execute("ALTER TABLE memory ADD COLUMN layer TEXT DEFAULT 'auto'")
    conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='memory_fts';
    """)
    # FTS legacy migration — only creates if missing (full repair via _ensure_memory_fts)
    fts_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_fts'"
    ).fetchone()
    if not fts_exists:
        _ensure_memory_fts(conn, force_repair=True)


def insert_row(
    conversation_id: str,
    role: str,
    content: str,
    tags: Optional[str],
    layer: str,
) -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        _ensure_memory_fts(conn, force_repair=False)
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO memory
                (conversation_id, role, content, tags, layer, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id, role, content,
                    tags or "", layer,
                    datetime.utcnow().isoformat(timespec="seconds") + "Z",
                )
            )
        except sqlite3.DatabaseError as e:
            if "memory_fts" not in str(e).lower():
                raise
            _ensure_memory_fts(conn, force_repair=True)
            cur.execute(
                """
                INSERT INTO memory
                (conversation_id, role, content, tags, layer, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id, role, content,
                    tags or "", layer,
                    datetime.utcnow().isoformat(timespec="seconds") + "Z",
                )
            )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def row_to_memory_dict(row) -> Dict:
    return {
        "id": row[0],
        "conversation_id": row[1],
        "role": row[2],
        "content": row[3],
        "tags": row[4],
        "layer": row[5],
        "created_at": row[6],
    }
