"""
config.infra.paths
==================
Dateisystem-Pfade & Logging-Level.

WORKSPACE_BASE: Root-Verzeichnis für Session-Workspaces (Chunking, Long-Context).
                Unterordner werden pro conversation_id angelegt.
LOG_LEVEL     : Python-Logging-Level (DEBUG / INFO / WARNING / ERROR).
"""
import os

WORKSPACE_BASE = os.getenv("WORKSPACE_BASE", "/tmp/trion/workspace")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
MASTER_SETTINGS_FILE = os.getenv("MASTER_SETTINGS_FILE", "/tmp/settings_master.json")


def get_custom_mcps_dir() -> str:
    return os.getenv("CUSTOM_MCPS_DIR", "/app/custom_mcps")


def get_plugins_dir() -> str:
    return os.getenv("TRION_PLUGINS_DIR", "/app/ui_plugins")
