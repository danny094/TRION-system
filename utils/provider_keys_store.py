from __future__ import annotations

import base64
import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from cryptography.fernet import Fernet, InvalidToken


_DB_PATH = Path(os.getenv("PROVIDER_KEYS_DB_PATH", "/app/data/provider_keys.db"))
_DEFAULT_MASTER_KEY = "trion-provider-keys-dev-key-change-me"


def _master_secret() -> str:
    return str(
        os.getenv("TRION_PROVIDER_KEYS_MASTER_KEY")
        or os.getenv("SECRET_MASTER_KEY")
        or _DEFAULT_MASTER_KEY
    ).strip()


def _fernet() -> Fernet:
    digest = hashlib.sha256(_master_secret().encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _get_db() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_keys (
            name TEXT PRIMARY KEY,
            value_enc TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _normalize_name(name: str) -> str:
    return str(name or "").strip().upper()


def _mask_value(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if len(raw) <= 8:
        return "*" * len(raw)
    return f"{raw[:4]}…{raw[-4:]}"


def _encrypt(value: str) -> str:
    return _fernet().encrypt(str(value or "").encode("utf-8")).decode("utf-8")


def _decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(str(token or "").encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def list_provider_keys() -> List[Dict[str, str]]:
    db = _get_db()
    rows = db.execute(
        "SELECT name, value_enc, updated_at FROM provider_keys ORDER BY updated_at DESC, name ASC"
    ).fetchall()
    return [
        {
            "id": str(row["name"]),
            "name": str(row["name"]),
            "masked_value": _mask_value(_decrypt(str(row["value_enc"]))),
            "last_modified": str(row["updated_at"]),
        }
        for row in rows
    ]


def upsert_provider_key(name: str, value: str) -> Dict[str, str]:
    key_name = _normalize_name(name)
    key_value = str(value or "").strip()
    updated_at = datetime.now(timezone.utc).isoformat()
    db = _get_db()
    db.execute(
        """
        INSERT INTO provider_keys (name, value_enc, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            value_enc=excluded.value_enc,
            updated_at=excluded.updated_at
        """,
        (key_name, _encrypt(key_value), updated_at),
    )
    db.commit()
    return {
        "id": key_name,
        "name": key_name,
        "masked_value": _mask_value(key_value),
        "last_modified": updated_at,
    }


def delete_provider_key(name: str) -> bool:
    key_name = _normalize_name(name)
    db = _get_db()
    cur = db.execute("DELETE FROM provider_keys WHERE name = ?", (key_name,))
    db.commit()
    return int(cur.rowcount or 0) > 0


def resolve_provider_key(name: str) -> str:
    key_name = _normalize_name(name)
    if not key_name:
        return ""
    db = _get_db()
    row = db.execute(
        "SELECT value_enc FROM provider_keys WHERE name = ?",
        (key_name,),
    ).fetchone()
    if not row:
        return ""
    return _decrypt(str(row["value_enc"]))
