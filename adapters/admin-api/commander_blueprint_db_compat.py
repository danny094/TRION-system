"""Shared blueprint DB compatibility helpers."""

from __future__ import annotations

import os

from commander_deploy_blueprints import ensure_store_initialized, get_conn as _get_conn


DB_PATH = os.environ.get("COMMANDER_DB_PATH", "/app/data/commander.db")


def init_db():
    """Compatibility entrypoint: ensure the localized commander store exists."""
    ensure_store_initialized()
