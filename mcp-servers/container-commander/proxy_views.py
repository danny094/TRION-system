from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from blueprint_store_db import get_conn
from contracts import error_result


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_tables() -> None:
    conn = get_conn()
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


def _normalize_domains(domains: list[Any] | None) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for item in list(domains or []):
        domain = str(item or "").strip().lower()
        if not domain or domain in seen:
            continue
        seen.add(domain)
        normalized.append(domain)
    return normalized


def ensure_proxy_running() -> dict[str, Any]:
    _ensure_tables()
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE proxy_state SET enabled = 1, updated_at = ? WHERE singleton_key = 'default'",
            (_now(),),
        )
        conn.commit()
        return {"started": True, "enabled": True}
    except Exception as exc:
        return error_result("PROXY_START_FAILED", str(exc))
    finally:
        conn.close()


def stop_proxy() -> dict[str, Any]:
    _ensure_tables()
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE proxy_state SET enabled = 0, updated_at = ? WHERE singleton_key = 'default'",
            (_now(),),
        )
        conn.commit()
        return {"stopped": True, "enabled": False}
    except Exception as exc:
        return error_result("PROXY_STOP_FAILED", str(exc))
    finally:
        conn.close()


def get_whitelist(blueprint_id: str) -> dict[str, Any]:
    safe_id = str(blueprint_id or "").strip()
    if not safe_id:
        return error_result("INVALID_BLUEPRINT_ID", "blueprint_id is required")
    _ensure_tables()
    conn = get_conn()
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
        return error_result("PROXY_WHITELIST_READ_FAILED", str(exc))
    finally:
        conn.close()


def set_whitelist(blueprint_id: str, domains: list[Any] | None) -> dict[str, Any]:
    safe_id = str(blueprint_id or "").strip()
    if not safe_id:
        return error_result("INVALID_BLUEPRINT_ID", "blueprint_id is required")
    _ensure_tables()
    normalized = _normalize_domains(domains)
    conn = get_conn()
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
        return error_result("PROXY_WHITELIST_WRITE_FAILED", str(exc))
    finally:
        conn.close()
