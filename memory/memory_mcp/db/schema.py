import os
import sqlite3

from ..config import DB_PATH
from .memory import create_memory_table, migrate_memory_table
from .facts import create_facts_table, migrate_facts_table
from .skill_metrics import create_skill_metrics_table, migrate_skill_metrics_table
from .workspace import create_workspace_table, migrate_workspace_table
from .conversation_meta import create_conversation_meta_table
from .secrets_table import create_secrets_table
from .artifacts import create_artifacts_table, migrate_artifacts_table
from .task_tables import create_task_tables, migrate_task_tables


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        create_memory_table(conn)
        create_facts_table(conn)
        create_skill_metrics_table(conn)
        create_workspace_table(conn)
        create_conversation_meta_table(conn)
        create_task_tables(conn)
        create_secrets_table(conn)
        create_artifacts_table(conn)
        conn.commit()
    finally:
        conn.close()


def migrate_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        migrate_memory_table(conn)
        migrate_facts_table(conn)
        migrate_skill_metrics_table(conn)
        migrate_workspace_table(conn)
        # conversation_meta: always idempotent via CREATE IF NOT EXISTS
        create_conversation_meta_table(conn)
        migrate_task_tables(conn)
        migrate_artifacts_table(conn)
        conn.commit()
    finally:
        conn.close()
