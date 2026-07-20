"""
Shared marketplace catalog helpers.

This module is the local truth for remote catalog fetch, normalization, and
cache handling used by legacy marketplace compatibility paths.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from commander_marketplace_paths import (
    MARKETPLACE_CATALOG_CACHE,
    MARKETPLACE_DEFAULT_CATALOG_BRANCH,
    MARKETPLACE_DEFAULT_CATALOG_REPO,
    MARKETPLACE_DIR,
)


def ensure_marketplace_dir() -> None:
    os.makedirs(MARKETPLACE_DIR, exist_ok=True)


def http_get_text(url: str, timeout: int = 20) -> str:
    req = Request(
        url=url,
        headers={
            "User-Agent": "TRION-Blueprint-Catalog/1.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def http_get_bytes(url: str, timeout: int = 20) -> bytes:
    req = Request(
        url=url,
        headers={
            "User-Agent": "TRION-Blueprint-Catalog/1.0",
            "Accept": "application/octet-stream,*/*",
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def resolve_github_raw(repo_url: str, branch: str = "main") -> Dict[str, str]:
    raw_input = str(repo_url or "").strip()
    if not raw_input:
        raise ValueError("repo_url is required")
    if not raw_input.startswith("http://") and not raw_input.startswith("https://"):
        raw_input = f"https://{raw_input}"

    parsed = urlparse(raw_input)
    host = (parsed.netloc or "").lower()
    path_parts = [p for p in (parsed.path or "").split("/") if p]
    target_branch = str(branch or "main").strip() or "main"

    if host in {"github.com", "www.github.com"}:
        if len(path_parts) < 2:
            raise ValueError("repo_url must be like https://github.com/<owner>/<repo>")
        owner = path_parts[0]
        repo = path_parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]
    elif host == "raw.githubusercontent.com":
        if len(path_parts) < 3:
            raise ValueError("raw github url must contain owner/repo/branch")
        owner = path_parts[0]
        repo = path_parts[1]
        target_branch = path_parts[2]
    else:
        raise ValueError("only github.com or raw.githubusercontent.com are supported")

    raw_base = f"https://raw.githubusercontent.com/{owner}/{repo}/{target_branch}/"
    index_url = urljoin(raw_base, "index.json")
    canonical_repo_url = f"https://github.com/{owner}/{repo}"
    return {
        "repo_url": canonical_repo_url,
        "branch": target_branch,
        "raw_base": raw_base,
        "index_url": index_url,
    }


def default_catalog_repo_from_settings() -> str:
    try:
        from utils.settings import settings as runtime_settings

        collections = runtime_settings.get("TRION_REFERENCE_LINK_COLLECTIONS", {})
        if not isinstance(collections, dict):
            return ""
        rows = collections.get("blueprints", [])
        if not isinstance(rows, list):
            return ""
        for row in rows:
            item = row if isinstance(row, dict) else {}
            if not bool(item.get("enabled", True)):
                continue
            url = str(item.get("url", "")).strip()
            if url:
                return url
    except Exception:
        return ""
    return ""


def normalize_health_profile(raw: Dict[str, Any]) -> Dict[str, int]:
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


def normalize_catalog_entry(raw: Dict[str, Any], raw_base: str) -> Dict[str, Any]:
    item = raw if isinstance(raw, dict) else {}
    bp_id = str(item.get("id", "")).strip()
    name = str(item.get("name", "")).strip()
    yaml_url = str(item.get("yaml_url", "")).strip()
    if not bp_id or not name or not yaml_url:
        raise ValueError("blueprint entry requires id, name, yaml_url")

    parsed_yaml = urlparse(yaml_url)
    resolved_yaml_url = yaml_url if parsed_yaml.scheme in {"http", "https"} else urljoin(raw_base, yaml_url)
    bundle_url = str(item.get("bundle_url", "")).strip()
    if bundle_url and not urlparse(bundle_url).scheme:
        bundle_url = urljoin(raw_base, bundle_url)
    package_url = str(item.get("package_url", "")).strip()
    if package_url and not urlparse(package_url).scheme:
        package_url = urljoin(raw_base, package_url)

    tags = [str(t).strip() for t in (item.get("tags") or []) if str(t).strip()]
    profile = normalize_health_profile(item.get("health_profile") or {})
    network = str(item.get("network", "internal")).strip().lower() or "internal"
    requires_approval = bool(item.get("requires_approval", False) or network == "full")

    return {
        "id": bp_id,
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
        "package_url": package_url,
        "package_type": str(item.get("package_type", "")).strip().lower(),
        "has_host_companion": bool(item.get("has_host_companion", False)),
        "supports_trion_addons": bool(item.get("supports_trion_addons", False)),
        "downloads": int(item.get("downloads", 0) or 0),
        "stars": int(item.get("stars", 0) or 0),
        "health_profile": profile,
    }


def load_catalog_cache() -> Dict[str, Any]:
    try:
        if not os.path.exists(MARKETPLACE_CATALOG_CACHE):
            return {}
        with open(MARKETPLACE_CATALOG_CACHE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_catalog_cache(payload: Dict[str, Any]) -> None:
    ensure_marketplace_dir()
    with open(MARKETPLACE_CATALOG_CACHE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def sync_remote_catalog(repo_url: str = "", branch: str = "main") -> Dict[str, Any]:
    source_url = str(repo_url or "").strip() or default_catalog_repo_from_settings() or MARKETPLACE_DEFAULT_CATALOG_REPO
    if not source_url:
        raise ValueError("repo_url missing: pass repo_url or configure settings reference-links (blueprints)")

    resolved = resolve_github_raw(source_url, branch=branch or MARKETPLACE_DEFAULT_CATALOG_BRANCH)
    raw_index = http_get_text(resolved["index_url"], timeout=20)
    payload = json.loads(raw_index)
    if not isinstance(payload, dict):
        raise ValueError("index.json must be an object")

    raw_blueprints = payload.get("blueprints") or []
    if not isinstance(raw_blueprints, list):
        raise ValueError("index.json: 'blueprints' must be a list")

    normalized: List[Dict[str, Any]] = []
    categories: Dict[str, int] = {}
    for entry in raw_blueprints:
        row = normalize_catalog_entry(entry if isinstance(entry, dict) else {}, resolved["raw_base"])
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
    save_catalog_cache(cache)
    return {
        "synced": True,
        "count": len(normalized),
        "categories": categories,
        "synced_at": now,
        "source": cache["source"],
        "schema_version": cache["schema_version"],
        "trion_compat": cache["trion_compat"],
    }


def get_catalog_cache() -> Dict[str, Any]:
    return load_catalog_cache()


def list_catalog(category: str = "", trusted_only: bool = False) -> Dict[str, Any]:
    cache = load_catalog_cache()
    rows = cache.get("blueprints") if isinstance(cache.get("blueprints"), list) else []
    requested_category = str(category or "").strip().lower()
    if requested_category:
        rows = [r for r in rows if str(r.get("category", "")).lower() == requested_category]
    if trusted_only:
        rows = [r for r in rows if str(r.get("trusted_level", "")).lower() in {"verified", "trusted"}]
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
