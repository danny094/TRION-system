from __future__ import annotations

import json
import logging

from commander_blueprint_trust import OFFICIAL_BLUEPRINT_IDS
from commander_blueprint_write import create_blueprint
from commander_deploy_blueprints import ensure_store_initialized, get_conn
from models import Blueprint, NetworkMode, ResourceLimits

logger = logging.getLogger(__name__)

_DEFAULT_EXEC_POLICIES = {
    "python-sandbox": ["python", "python3", "pip", "pip3", "sh", "bash"],
    "node-sandbox": ["node", "npm", "npx", "yarn", "sh", "bash"],
    "db-sandbox": ["python", "python3", "pip", "pip3", "sqlite3", "sh", "bash"],
    "shell-sandbox": [
        "sh",
        "ash",
        "bash",
        "ls",
        "cat",
        "grep",
        "echo",
        "curl",
        "wget",
        "jq",
        "awk",
        "sed",
        "find",
        "ps",
        "df",
        "du",
        "env",
        "printenv",
        "uname",
        "hostname",
    ],
    "ubuntu-network": [
        "sh",
        "bash",
        "apt",
        "apt-get",
        "curl",
        "wget",
        "ping",
        "dig",
        "nslookup",
        "ip",
        "ss",
        "netstat",
        "ls",
        "cat",
        "grep",
        "echo",
        "awk",
        "sed",
        "find",
        "ps",
        "df",
        "du",
        "env",
        "printenv",
        "uname",
        "hostname",
    ],
}

_DEFAULTS = [
    Blueprint(
        id="python-sandbox",
        name="Python Sandbox",
        description="Isolierte Python-Umgebung mit pip. Fuer Berechnungen, Datenanalyse, Scripts.",
        image="python:3.12-slim",
        icon="\U0001f40d",
        resources=ResourceLimits(cpu_limit="1.0", memory_limit="512m", timeout_seconds=600),
        tags=["python", "sandbox", "code", "compute"],
        allowed_exec=["python", "python3", "pip", "pip3", "sh", "bash"],
    ),
    Blueprint(
        id="node-sandbox",
        name="Node.js Sandbox",
        description="Isolierte Node.js-Umgebung mit npm. Fuer JavaScript, TypeScript, Web-Tools.",
        image="node:20-slim",
        icon="\U0001f7e2",
        resources=ResourceLimits(cpu_limit="1.0", memory_limit="512m", timeout_seconds=600),
        tags=["node", "javascript", "sandbox", "web"],
        allowed_exec=["node", "npm", "npx", "yarn", "sh", "bash"],
    ),
    Blueprint(
        id="db-sandbox",
        name="Database Sandbox",
        description="SQLite/PostgreSQL-Umgebung fuer Datenbankoperationen und SQL-Queries.",
        image="python:3.12-slim",
        icon="\U0001f5c4",
        resources=ResourceLimits(cpu_limit="0.5", memory_limit="256m", timeout_seconds=300),
        tags=["database", "sql", "sqlite", "data"],
        allowed_exec=["python", "python3", "pip", "pip3", "sqlite3", "sh", "bash"],
    ),
    Blueprint(
        id="shell-sandbox",
        name="Shell Sandbox",
        description="Alpine-basierte Shell-Umgebung fuer Systemtools, curl, jq, etc.",
        image="alpine:latest",
        icon="\U0001f41a",
        resources=ResourceLimits(cpu_limit="0.5", memory_limit="256m", timeout_seconds=300),
        tags=["shell", "linux", "tools", "system"],
        allowed_exec=[
            "sh",
            "ash",
            "bash",
            "ls",
            "cat",
            "grep",
            "echo",
            "curl",
            "wget",
            "jq",
            "awk",
            "sed",
            "find",
            "ps",
            "df",
            "du",
            "env",
            "printenv",
            "uname",
            "hostname",
        ],
    ),
    Blueprint(
        id="ubuntu-network",
        name="Ubuntu Network Sandbox",
        description="Ubuntu 24.04 Shell-Umgebung mit Bridge-Netzwerkzugang und Basis-Netzwerktools.",
        dockerfile="""FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \\
    && apt-get install -y --no-install-recommends \\
        bash ca-certificates curl dnsutils iproute2 iputils-ping net-tools wget \\
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
CMD ["sleep", "infinity"]
""",
        icon="\U0001f310",
        resources=ResourceLimits(cpu_limit="1.0", memory_limit="1g", memory_swap="2g", timeout_seconds=1800),
        network=NetworkMode.BRIDGE,
        tags=["ubuntu", "linux", "network", "shell", "tools"],
        allowed_exec=[
            "sh",
            "bash",
            "apt",
            "apt-get",
            "curl",
            "wget",
            "ping",
            "dig",
            "nslookup",
            "ip",
            "ss",
            "netstat",
            "ls",
            "cat",
            "grep",
            "echo",
            "awk",
            "sed",
            "find",
            "ps",
            "df",
            "du",
            "env",
            "printenv",
            "uname",
            "hostname",
        ],
    ),
]


def get_active_blueprint_ids() -> set[str]:
    ensure_store_initialized()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id FROM blueprints WHERE (is_deleted IS NULL OR is_deleted = 0)"
        ).fetchall()
        return {str(row["id"]) for row in rows if row["id"]}
    finally:
        conn.close()


def seed_default_blueprints() -> None:
    existing_ids = get_active_blueprint_ids()
    seeded = 0
    for blueprint in _DEFAULTS:
        if blueprint.id in existing_ids:
            continue
        try:
            create_blueprint(blueprint.model_dump())
            seeded += 1
        except Exception:
            pass
    if seeded:
        logger.info("[BlueprintSeeds] Seeded %s missing built-in blueprints", seeded)


def backfill_exec_policies() -> None:
    ensure_store_initialized()
    conn = get_conn()
    try:
        updated = 0
        for blueprint_id, policy in _DEFAULT_EXEC_POLICIES.items():
            row = conn.execute(
                "SELECT exec_policy_json FROM blueprints WHERE id = ?",
                (blueprint_id,),
            ).fetchone()
            if row is None:
                continue
            current = json.loads(row["exec_policy_json"] or "[]")
            if current:
                continue
            conn.execute(
                "UPDATE blueprints SET exec_policy_json = ? WHERE id = ?",
                (json.dumps(policy), blueprint_id),
            )
            updated += 1
        conn.commit()
        if updated:
            logger.info("[BlueprintSeeds] Backfilled exec policies for %s blueprints", updated)
    finally:
        conn.close()
