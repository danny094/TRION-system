#!/usr/bin/env python3
import json
import os
import tarfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


MARKETPLACE_DIR = os.environ.get("MARKETPLACE_DIR", "/app/data/marketplace")
MARKETPLACE_CATALOG_CACHE = os.environ.get(
    "MARKETPLACE_CATALOG_CACHE",
    os.path.join(MARKETPLACE_DIR, "catalog_cache.json"),
)
MARKETPLACE_DEFAULT_CATALOG_REPO = os.environ.get("TRION_BLUEPRINT_CATALOG_REPO", "")
MARKETPLACE_DEFAULT_CATALOG_BRANCH = os.environ.get("TRION_BLUEPRINT_CATALOG_BRANCH", "main")

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
]


def _ensure_marketplace_dir():
    os.makedirs(MARKETPLACE_DIR, exist_ok=True)


def list_bundles():
    if not os.path.exists(MARKETPLACE_DIR):
        return []
    result = []
    for filename in sorted(os.listdir(MARKETPLACE_DIR)):
        if not filename.endswith(".trion-bundle.tar.gz"):
            continue
        filepath = os.path.join(MARKETPLACE_DIR, filename)
        stat = os.stat(filepath)
        meta = {}
        try:
            with tarfile.open(filepath, "r:gz") as tar:
                meta_raw = tar.extractfile("meta.json").read().decode("utf-8")
                meta = json.loads(meta_raw)
        except Exception:
            meta = {}
        result.append(
            {
                "filename": filename,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "id": meta.get("id", filename.replace(".trion-bundle.tar.gz", "")),
                "name": meta.get("name", ""),
                "version": meta.get("version", ""),
                "tags": meta.get("tags", []),
                "exported_at": meta.get("exported_at", ""),
            }
        )
    return result


def get_starters():
    return list(STARTER_BLUEPRINTS)


def _http_get_text(url: str, timeout: int = 20) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "TRION-Blueprint-Catalog/1.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _resolve_github_raw(repo_url: str, branch: str = "main") -> dict:
    raw_input = str(repo_url or "").strip()
    if not raw_input:
        raise ValueError("repo_url is required")
    if not raw_input.startswith("http://") and not raw_input.startswith("https://"):
        raw_input = f"https://{raw_input}"
    parsed = urlparse(raw_input)
    host = (parsed.netloc or "").lower()
    path_parts = [part for part in (parsed.path or "").split("/") if part]
    target_branch = str(branch or "main").strip() or "main"
    if host in {"github.com", "www.github.com"}:
        if len(path_parts) < 2:
            raise ValueError("repo_url must be like https://github.com/<owner>/<repo>")
        owner = path_parts[0]
        repo = path_parts[1][:-4] if path_parts[1].endswith(".git") else path_parts[1]
    elif host == "raw.githubusercontent.com":
        if len(path_parts) < 3:
            raise ValueError("raw github url must contain owner/repo/branch")
        owner = path_parts[0]
        repo = path_parts[1]
        target_branch = path_parts[2]
    else:
        raise ValueError("only github.com or raw.githubusercontent.com are supported")
    raw_base = f"https://raw.githubusercontent.com/{owner}/{repo}/{target_branch}/"
    return {
        "repo_url": f"https://github.com/{owner}/{repo}",
        "branch": target_branch,
        "raw_base": raw_base,
        "index_url": urljoin(raw_base, "index.json"),
    }


def _normalize_health_profile(raw):
    data = raw if isinstance(raw, dict) else {}

    def _to_int(key: str, fallback: int) -> int:
        try:
            value = int(float(data.get(key, fallback)))
        except Exception:
            value = fallback
        return max(1, min(3600, value))

    ready_timeout = _to_int("ready_timeout_seconds", _to_int("timeout", 60))
    interval = _to_int("interval_seconds", _to_int("check_interval", 15))
    timeout = _to_int("timeout_seconds", 5)
    retries = _to_int("retries", 3)
    return {
        "ready_timeout_seconds": ready_timeout,
        "interval_seconds": interval,
        "timeout_seconds": timeout,
        "retries": retries,
    }


def _normalize_catalog_entry(raw, raw_base: str):
    item = raw if isinstance(raw, dict) else {}
    blueprint_id = str(item.get("id", "")).strip()
    name = str(item.get("name", "")).strip()
    yaml_url = str(item.get("yaml_url", "")).strip()
    if not blueprint_id or not name or not yaml_url:
        raise ValueError("blueprint entry requires id, name, yaml_url")
    resolved_yaml_url = yaml_url if urlparse(yaml_url).scheme in {"http", "https"} else urljoin(raw_base, yaml_url)
    bundle_url = str(item.get("bundle_url", "")).strip()
    if bundle_url and not urlparse(bundle_url).scheme:
        bundle_url = urljoin(raw_base, bundle_url)
    tags = [str(tag).strip() for tag in (item.get("tags") or []) if str(tag).strip()]
    profile = _normalize_health_profile(item.get("health_profile") or {})
    network = str(item.get("network", "internal")).strip().lower() or "internal"
    requires_approval = bool(item.get("requires_approval", False) or network == "full")
    return {
        "id": blueprint_id,
        "name": name,
        "description": str(item.get("description", "")).strip(),
        "category": str(item.get("category", "uncategorized")).strip().lower() or "uncategorized",
        "tags": tags,
        "icon": str(item.get("icon", "📦")).strip() or "📦",
        "difficulty": str(item.get("difficulty", "")).strip().lower(),
        "network": network,
        "requires_secrets": bool(item.get("requires_secrets", False)),
        "requires_runtime": str(item.get("requires_runtime", "none")).strip().lower() or "none",
        "requires_approval": requires_approval,
        "requires_gpu": bool(item.get("requires_gpu", False)),
        "trusted_level": str(item.get("trusted_level", "unverified")).strip().lower() or "unverified",
        "author": str(item.get("author", "")).strip(),
        "version": str(item.get("version", "1.0.0")).strip() or "1.0.0",
        "yaml_url": resolved_yaml_url,
        "bundle_url": bundle_url,
        "package_type": str(item.get("package_type", "")).strip().lower(),
        "has_host_companion": bool(item.get("has_host_companion", False)),
        "supports_trion_addons": bool(item.get("supports_trion_addons", False)),
        "downloads": int(item.get("downloads", 0) or 0),
        "stars": int(item.get("stars", 0) or 0),
        "health_profile": profile,
    }


def _load_catalog_cache():
    try:
        if not os.path.exists(MARKETPLACE_CATALOG_CACHE):
            return {}
        with open(MARKETPLACE_CATALOG_CACHE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_catalog_cache(payload):
    _ensure_marketplace_dir()
    with open(MARKETPLACE_CATALOG_CACHE, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def sync_remote_catalog(repo_url: str = "", branch: str = "main"):
    source_url = str(repo_url or "").strip() or MARKETPLACE_DEFAULT_CATALOG_REPO
    if not source_url:
        raise ValueError("repo_url missing: pass repo_url or configure TRION_BLUEPRINT_CATALOG_REPO")
    resolved = _resolve_github_raw(source_url, branch=branch or MARKETPLACE_DEFAULT_CATALOG_BRANCH)
    raw_index = _http_get_text(resolved["index_url"], timeout=20)
    payload = json.loads(raw_index)
    if not isinstance(payload, dict):
        raise ValueError("index.json must be an object")
    raw_blueprints = payload.get("blueprints") or []
    if not isinstance(raw_blueprints, list):
        raise ValueError("index.json: 'blueprints' must be a list")
    normalized = []
    categories = {}
    for entry in raw_blueprints:
        row = _normalize_catalog_entry(entry if isinstance(entry, dict) else {}, resolved["raw_base"])
        normalized.append(row)
        categories[row["category"]] = int(categories.get(row["category"], 0)) + 1
    now = datetime.utcnow().isoformat() + "Z"
    cache = {
        "schema_version": str(payload.get("schema_version", "1.0.0")),
        "trion_compat": payload.get("trion_compat") if isinstance(payload.get("trion_compat"), dict) else {},
        "synced_at": now,
        "source": {
            "repo_url": resolved["repo_url"],
            "branch": resolved["branch"],
            "index_url": resolved["index_url"],
            "raw_base": resolved["raw_base"],
        },
        "categories": categories,
        "blueprints": normalized,
    }
    _save_catalog_cache(cache)
    return {
        "synced": True,
        "count": len(normalized),
        "categories": categories,
        "synced_at": now,
        "source": cache["source"],
        "schema_version": cache["schema_version"],
        "trion_compat": cache["trion_compat"],
    }


def list_catalog(category: str = "", trusted_only: bool = False):
    cache = _load_catalog_cache()
    rows = cache.get("blueprints") if isinstance(cache.get("blueprints"), list) else []
    requested_category = str(category or "").strip().lower()
    if requested_category:
        rows = [row for row in rows if str(row.get("category", "")).lower() == requested_category]
    if trusted_only:
        rows = [row for row in rows if str(row.get("trusted_level", "")).lower() in {"verified", "trusted"}]
    return {
        "source": cache.get("source", {}),
        "schema_version": cache.get("schema_version", ""),
        "trion_compat": cache.get("trion_compat", {}),
        "synced_at": cache.get("synced_at", ""),
        "categories": cache.get("categories", {}),
        "blueprints": rows,
        "count": len(rows),
        "category": requested_category or "all",
        "trusted_only": bool(trusted_only),
    }
