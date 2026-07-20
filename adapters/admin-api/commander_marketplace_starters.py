"""
Shared marketplace starter helpers.

This module is the local truth for built-in starter blueprints and their
install flow.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from commander_blueprint_write import create_blueprint
from commander_deploy_blueprints import get_blueprint
from models import Blueprint, NetworkMode, ResourceLimits


STARTER_BLUEPRINTS = [
    {
        "id": "python-sandbox",
        "name": "Python Sandbox",
        "description": "Python 3.12 with pip, numpy, pandas. Ideal for data analysis and scripting.",
        "icon": "🐍",
        "tags": ["python", "data", "starter"],
        "network": "none",
        "dockerfile": "FROM python:3.12-slim\nRUN pip install --no-cache-dir numpy pandas matplotlib requests\nWORKDIR /workspace\nCMD [\"python3\", \"-i\"]",
        "resources": {"cpu_limit": "1.0", "memory_limit": "512m", "timeout_seconds": 600},
    },
    {
        "id": "node-sandbox",
        "name": "Node.js Sandbox",
        "description": "Node.js 20 LTS with npm. For JS/TS development and scripting.",
        "icon": "🟢",
        "tags": ["node", "javascript", "starter"],
        "network": "none",
        "dockerfile": "FROM node:20-slim\nWORKDIR /workspace\nCMD [\"node\"]",
        "resources": {"cpu_limit": "1.0", "memory_limit": "512m", "timeout_seconds": 600},
    },
    {
        "id": "web-scraper",
        "name": "Web Scraper",
        "description": "Python with BeautifulSoup, Selenium, playwright. Needs internet (approval required).",
        "icon": "🕷️",
        "tags": ["python", "web", "scraping"],
        "network": "full",
        "allowed_domains": ["*.github.com", "*.stackoverflow.com"],
        "dockerfile": "FROM python:3.12-slim\nRUN pip install --no-cache-dir beautifulsoup4 requests lxml httpx\nWORKDIR /workspace\nCMD [\"python3\", \"-i\"]",
        "resources": {"cpu_limit": "0.5", "memory_limit": "256m", "timeout_seconds": 300},
    },
    {
        "id": "db-sandbox",
        "name": "Database Sandbox",
        "description": "SQLite + PostgreSQL client tools for database work.",
        "icon": "🗄️",
        "tags": ["database", "sql", "starter"],
        "network": "internal",
        "dockerfile": "FROM python:3.12-slim\nRUN pip install --no-cache-dir sqlalchemy psycopg2-binary sqlite-utils\nRUN apt-get update && apt-get install -y --no-install-recommends postgresql-client sqlite3 && rm -rf /var/lib/apt/lists/*\nWORKDIR /workspace\nCMD [\"python3\", \"-i\"]",
        "resources": {"cpu_limit": "0.5", "memory_limit": "256m", "timeout_seconds": 300},
    },
    {
        "id": "latex-builder",
        "name": "LaTeX Builder",
        "description": "Full TeX Live for PDF document generation.",
        "icon": "📄",
        "tags": ["latex", "pdf", "documents"],
        "network": "none",
        "dockerfile": "FROM texlive/texlive:latest-minimal\nRUN tlmgr install collection-basic collection-latex collection-fontsrecommended\nWORKDIR /workspace\nCMD [\"/bin/sh\"]",
        "resources": {"cpu_limit": "2.0", "memory_limit": "1g", "timeout_seconds": 900},
    },
]


def get_starters() -> List[Dict]:
    return STARTER_BLUEPRINTS


def install_starter(starter_id: str) -> Optional[Dict]:
    starter = next((s for s in STARTER_BLUEPRINTS if s["id"] == starter_id), None)
    if not starter:
        return {"error": f"Starter '{starter_id}' not found"}

    existing = get_blueprint(starter_id)
    if existing:
        return {"exists": True, "blueprint": existing.model_dump()}

    data = dict(starter)
    resources = ResourceLimits(**(data.pop("resources", {})))
    network = NetworkMode(data.pop("network", "internal"))
    data.pop("allowed_domains", None)

    bp = Blueprint(resources=resources, network=network, **data)
    create_blueprint(bp.model_dump())
    created = get_blueprint(starter_id)
    return {"installed": True, "blueprint": created.model_dump() if created else bp.model_dump()}
