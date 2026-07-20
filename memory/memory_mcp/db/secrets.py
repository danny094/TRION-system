import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from ..config import DB_PATH


def _get_cipher():
    import base64
    import hashlib
    from cryptography.fernet import Fernet
    master = os.getenv("SECRET_MASTER_KEY", "trion-default-secret-key-change-me")
    key = base64.urlsafe_b64encode(hashlib.sha256(master.encode()).digest())
    return Fernet(key)


def save_secret(name: str, value: str) -> None:
    cipher = _get_cipher()
    encrypted = cipher.encrypt(value.encode()).decode()
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO secrets (name, encrypted_value, created_at, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET encrypted_value=excluded.encrypted_value, updated_at=excluded.updated_at",
            (name, encrypted, now, now)
        )
        conn.commit()
    finally:
        conn.close()


def get_secret_value(name: str) -> Optional[str]:
    cipher = _get_cipher()
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT encrypted_value FROM secrets WHERE name=?", (name,)
        ).fetchone()
        if not row:
            return None
        return cipher.decrypt(row[0].encode()).decode()
    finally:
        conn.close()


def list_secrets() -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT name, created_at, updated_at FROM secrets ORDER BY name"
        ).fetchall()
        return [{"name": r[0], "created_at": r[1], "updated_at": r[2]} for r in rows]
    finally:
        conn.close()


def delete_secret(name: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("DELETE FROM secrets WHERE name=?", (name,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
