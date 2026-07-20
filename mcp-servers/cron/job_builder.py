from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple


def collect_keyword_hits(text: str, keywords: Tuple[str, ...]) -> List[str]:
    raw = str(text or "").lower()
    hits: List[str] = []
    for key in keywords:
        token = str(key or "").strip().lower()
        if not token:
            continue
        if " " in token or "-" in token or "/" in token:
            if token in raw:
                hits.append(token)
            continue
        if re.search(rf"\b{re.escape(token)}\b", raw):
            hits.append(token)
    return list(dict.fromkeys(hits))


def normalize_reference_links(raw: Any, *, max_items: int = 12) -> List[Dict[str, Any]]:
    rows = raw if isinstance(raw, list) else []
    out: List[Dict[str, Any]] = []
    seen_urls: Set[str] = set()
    for entry in rows:
        item = entry if isinstance(entry, dict) else {}
        name = str(item.get("name", "")).strip()
        url = str(item.get("url", "")).strip()
        if not name or not url:
            continue
        key = url.lower()
        if key in seen_urls:
            continue
        seen_urls.add(key)
        out.append({
            "name": name[:120],
            "url": url[:500],
            "description": str(item.get("description", "")).strip()[:300],
            "read_only": True,
        })
        if len(out) >= max(1, int(max_items)):
            break
    return out


def build_default_job_note_md(job: Dict[str, Any]) -> str:
    data = job if isinstance(job, dict) else {}
    name = str(data.get("name", "")).strip() or "cron-job"
    objective = str(data.get("objective", "")).strip() or "No objective provided."
    schedule_mode = str(data.get("schedule_mode", "recurring")).strip().lower() or "recurring"
    timezone_name = str(data.get("timezone", "UTC")).strip() or "UTC"
    created_by = str(data.get("created_by", "user")).strip() or "user"
    conversation_id = str(data.get("conversation_id", "")).strip() or "-"
    try:
        max_loops = int(data.get("max_loops", 1) or 1)
    except Exception:
        max_loops = 1

    lines = [f"# Cron Job: {name}", "", "## Objective", objective[:1000], "", "## Schedule",
             f"- Mode: `{schedule_mode}`"]
    if schedule_mode == "one_shot":
        lines.append(f"- Run at (UTC): `{str(data.get('run_at', '')).strip() or '-'}`")
    else:
        lines.append(f"- Cron: `{str(data.get('cron', '')).strip() or '-'}`")
    lines.extend([
        f"- Timezone: `{timezone_name}`", "", "## Runtime",
        f"- Created by: `{created_by}`",
        f"- Conversation: `{conversation_id}`",
        f"- Max loops: `{max_loops}`",
    ])
    return "\n".join(lines).strip()[:6000]
