import sqlite3


def create_task_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_active (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            importance_score FLOAT DEFAULT 0.0,
            UNIQUE(task_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_task_active_conv ON task_active(conversation_id, last_updated DESC)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            content TEXT NOT NULL,
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            embedding_id INTEGER,
            UNIQUE(task_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_task_archive_conv ON task_archive(conversation_id)"
    )
    _create_embeddings_table(conn)


def _create_embeddings_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            content TEXT NOT NULL,
            content_type TEXT DEFAULT 'fact',
            metadata TEXT,
            embedding BLOB,
            embedding_model TEXT,
            embedding_dim INTEGER,
            embedding_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    emb_cols = [r[1] for r in conn.execute("PRAGMA table_info(embeddings)").fetchall()]
    for col, col_type in [
        ("embedding_model", "TEXT"),
        ("embedding_dim", "INTEGER"),
        ("embedding_version", "TEXT"),
    ]:
        if col not in emb_cols:
            conn.execute(f"ALTER TABLE embeddings ADD COLUMN {col} {col_type}")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_embeddings_conv ON embeddings(conversation_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_embeddings_version ON embeddings(embedding_version)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_embeddings_type_version ON embeddings(content_type, embedding_version)"
    )


def migrate_task_tables(conn: sqlite3.Connection) -> None:
    for table in ("task_active", "task_archive"):
        exists = conn.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
        ).fetchone()
        if not exists:
            create_task_tables(conn)
            return
    _create_embeddings_table(conn)
    # graph_nodes: add confidence column if missing
    if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='graph_nodes'").fetchone():
        graph_cols = [r[1] for r in conn.execute("PRAGMA table_info(graph_nodes)").fetchall()]
        if "confidence" not in graph_cols:
            conn.execute("ALTER TABLE graph_nodes ADD COLUMN confidence REAL DEFAULT 0.5")
