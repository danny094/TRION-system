import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

from ..config import DB_PATH
from utils.memory_defaults import (
    get_default_do_not_remember_value,
    get_default_memory_mode_value,
    parse_bool,
)


def create_conversation_meta_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_meta (
            conversation_id TEXT PRIMARY KEY,
            title TEXT,
            status_json TEXT,
            memory_json TEXT,
            runtime_scope_json TEXT,
            routing_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )


def get_conversation_meta(conversation_id: str) -> Optional[Dict]:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            """
            SELECT conversation_id, title, status_json, memory_json,
                   runtime_scope_json, routing_json, created_at, updated_at
            FROM conversation_meta WHERE conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "conversation_id": row[0],
            "title": row[1] or "",
            "status": json.loads(row[2]) if row[2] else {},
            "memory": json.loads(row[3]) if row[3] else {},
            "runtime_scope": json.loads(row[4]) if row[4] else {},
            "routing": json.loads(row[5]) if row[5] else {},
            "created_at": row[6],
            "updated_at": row[7],
        }
    finally:
        conn.close()


def upsert_conversation_meta(conversation_id: str, meta: Dict) -> Dict:
    conn = sqlite3.connect(DB_PATH)
    try:
        existing = get_conversation_meta(conversation_id)
        created_at = (
            existing.get("created_at")
            if isinstance(existing, dict) and existing.get("created_at")
            else datetime.utcnow().isoformat(timespec="seconds") + "Z"
        )
        updated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        conn.execute(
            """
            INSERT INTO conversation_meta
            (conversation_id, title, status_json, memory_json, runtime_scope_json, routing_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                title=excluded.title,
                status_json=excluded.status_json,
                memory_json=excluded.memory_json,
                runtime_scope_json=excluded.runtime_scope_json,
                routing_json=excluded.routing_json,
                updated_at=excluded.updated_at
            """,
            (
                conversation_id,
                str(meta.get("title", "") or ""),
                json.dumps(meta.get("status") or {}),
                json.dumps(meta.get("memory") or {}),
                json.dumps(meta.get("runtime_scope") or {}),
                json.dumps(meta.get("routing") or {}),
                created_at,
                updated_at,
            ),
        )
        conn.commit()
        return get_conversation_meta(conversation_id) or {"conversation_id": conversation_id}
    finally:
        conn.close()


def get_conversation_write_policy(conversation_id: str) -> Dict[str, Any]:
    meta = get_conversation_meta(conversation_id) or {}
    status = meta.get("status") if isinstance(meta.get("status"), dict) else {}
    memory = meta.get("memory") if isinstance(meta.get("memory"), dict) else {}
    mode = str(memory.get("mode") or get_default_memory_mode_value()).strip() or get_default_memory_mode_value()
    if mode not in {"global_enabled", "conversation_only", "disabled"}:
        mode = get_default_memory_mode_value()
    temporary = bool(status.get("temporary", False))
    do_not_remember = (
        parse_bool(memory.get("do_not_remember"), get_default_do_not_remember_value())
        if "do_not_remember" in memory
        else get_default_do_not_remember_value()
    )
    allow_long_term_write = mode != "disabled" and not temporary and not do_not_remember
    return {
        "conversation_id": str(conversation_id or "global").strip() or "global",
        "memory_mode": mode,
        "temporary": temporary,
        "do_not_remember": do_not_remember,
        "allow_long_term_write": allow_long_term_write,
    }


def evaluate_retrieval_policy(conversation_id: str) -> Dict[str, Any]:
    """
    Gibt Retrieval-Policy für eine Conversation zurück.

    allowed=False           → nichts zurückgeben (mode=disabled)
    conversation_scoped=True → nur Daten dieser Conversation (mode=conversation_only)
    conversation_scoped=False → globale Retrieval-Nutzung erlaubt
    """
    policy = get_conversation_write_policy(conversation_id)
    mode = policy["memory_mode"]
    if mode == "disabled":
        return {"allowed": False, "conversation_scoped": False, "reason": "memory_disabled", "policy": policy}
    if mode == "conversation_only":
        return {"allowed": True, "conversation_scoped": True, "reason": "conversation_only", "policy": policy}
    return {"allowed": True, "conversation_scoped": False, "reason": "global_enabled", "policy": policy}


def evaluate_long_term_write(conversation_id: str, layer: str) -> Dict[str, Any]:
    policy = get_conversation_write_policy(conversation_id)
    layer_norm = str(layer or "ltm").strip().lower() or "ltm"
    if layer_norm != "ltm":
        return {
            "allowed": True,
            "reason": "non_long_term_layer",
            "policy": policy,
        }
    if policy["allow_long_term_write"]:
        return {
            "allowed": True,
            "reason": "allowed",
            "policy": policy,
        }
    if policy["temporary"]:
        reason = "temporary_conversation"
    elif policy["do_not_remember"]:
        reason = "do_not_remember"
    elif policy["memory_mode"] == "disabled":
        reason = "memory_disabled"
    else:
        reason = "long_term_write_blocked"
    return {
        "allowed": False,
        "reason": reason,
        "policy": policy,
    }
