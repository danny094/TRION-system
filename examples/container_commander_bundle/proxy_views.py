#!/usr/bin/env python3
import json
import os
import sqlite3
from datetime import datetime, timezone


def _db_path():
    return os.environ.get("COMMANDER_DB_PATH", "/app/data/commander.db")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _error_result(code, message, retryable=False):
    return {"ok": False, "error": {"code": code, "message": message, "retryable": retryable}}


def _get_conn():
    db_path = _db_path()
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables():
    conn = _get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS proxy_state (
                singleton_key TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS proxy_whitelists (
                blueprint_id TEXT PRIMARY KEY,
                domains_json TEXT DEFAULT '[]',
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO proxy_state (singleton_key, enabled, updated_at)
            VALUES ('default', 0, ?)
            """,
            (_now(),),
        )
        conn.commit()
    finally:
        conn.close()


def _normalize_domains(domains):
    seen = set()
    normalized = []
    for item in list(domains or []):
        domain = str(item or "").strip().lower()
        if not domain or domain in seen:
            continue
        seen.add(domain)
        normalized.append(domain)
    return normalized


def ensure_proxy_running():
    _ensure_tables()
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE proxy_state SET enabled = 1, updated_at = ? WHERE singleton_key = 'default'",
            (_now(),),
        )
        conn.commit()
        return {"started": True, "enabled": True}
    except Exception as exc:
        return _error_result("PROXY_START_FAILED", str(exc))
    finally:
        conn.close()


def stop_proxy():
    _ensure_tables()
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE proxy_state SET enabled = 0, updated_at = ? WHERE singleton_key = 'default'",
            (_now(),),
        )
        conn.commit()
        return {"stopped": True, "enabled": False}
    except Exception as exc:
        return _error_result("PROXY_STOP_FAILED", str(exc))
    finally:
        conn.close()


def get_whitelist(blueprint_id):
    safe_id = str(blueprint_id or "").strip()
    if not safe_id:
        return _error_result("INVALID_BLUEPRINT_ID", "blueprint_id is required")
    _ensure_tables()
    conn = _get_conn()
    try:
        state_row = conn.execute(
            "SELECT enabled FROM proxy_state WHERE singleton_key = 'default'"
        ).fetchone()
        row = conn.execute(
            "SELECT domains_json FROM proxy_whitelists WHERE blueprint_id = ?",
            (safe_id,),
        ).fetchone()
        raw_domains = row["domains_json"] if row and row["domains_json"] else "[]"
        try:
            domains = json.loads(raw_domains)
        except Exception:
            domains = []
        return {
            "blueprint_id": safe_id,
            "domains": _normalize_domains(domains if isinstance(domains, list) else []),
            "enabled": bool(int(state_row["enabled"])) if state_row else False,
        }
    except Exception as exc:
        return _error_result("PROXY_WHITELIST_READ_FAILED", str(exc))
    finally:
        conn.close()


def set_whitelist(blueprint_id, domains):
    safe_id = str(blueprint_id or "").strip()
    if not safe_id:
        return _error_result("INVALID_BLUEPRINT_ID", "blueprint_id is required")
    _ensure_tables()
    normalized = _normalize_domains(domains)
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO proxy_whitelists (blueprint_id, domains_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(blueprint_id) DO UPDATE SET
                domains_json = excluded.domains_json,
                updated_at = excluded.updated_at
            """,
            (safe_id, json.dumps(normalized), _now()),
        )
        conn.commit()
        return {"updated": True, "blueprint_id": safe_id, "domains": normalized}
    except Exception as exc:
        return _error_result("PROXY_WHITELIST_WRITE_FAILED", str(exc))
    finally:
        conn.close()
