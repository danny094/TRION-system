#!/usr/bin/env python3
"""Check local Markdown and Obsidian-style links in docs/ without editing them."""
from __future__ import annotations

import re
import sys
from pathlib import Path

MARKDOWN_LINK = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")
WIKI_LINK = re.compile(r"\[\[([^]|#]+)(?:[|#][^]]*)?\]\]")
EXTERNAL = re.compile(r"^(?:https?://|mailto:|#)", re.IGNORECASE)
LINE_SUFFIX = re.compile(r":\d+(?::\d+)?$")


def docs_files(docs: Path) -> list[Path]:
    return sorted(
        path
        for path in docs.rglob("*.md")
        if "archive" not in path.parts and not path.name.startswith("README-freeze-status-")
    )


def target_files(docs: Path) -> list[Path]:
    return sorted(docs.rglob("*.md"))


def wiki_targets(files: list[Path]) -> dict[str, list[Path]]:
    targets: dict[str, list[Path]] = {}
    for path in files:
        targets.setdefault(path.stem, []).append(path)
    return targets


def markdown_target(path: Path, target: str, docs: Path) -> bool:
    target = LINE_SUFFIX.sub("", target.strip().split("#", 1)[0])
    if not target or EXTERNAL.match(target):
        return True
    candidate = Path(target)
    if candidate.is_absolute() or target.lower().startswith("file:"):
        return False
    return (path.parent / target).exists() or (docs / target).exists()


def wiki_target(path: Path, target: str, docs: Path, targets: dict[str, list[Path]]) -> bool:
    target = target.strip().rstrip("\\")
    if not target or target == "^":
        return True
    if "/" not in target:
        candidates = targets.get(target, [])
        active = [candidate for candidate in candidates if "archive" not in candidate.relative_to(docs).parts]
        return len(active or candidates) == 1
    suffix = "" if target.endswith(".md") else ".md"
    return any(candidate.exists() for candidate in (path.parent / f"{target}{suffix}", docs / f"{target}{suffix}"))


def missing_links(docs: Path) -> list[str]:
    files = docs_files(docs)
    targets = wiki_targets(target_files(docs))
    findings = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for target in MARKDOWN_LINK.findall(text):
            if not markdown_target(path, target, docs):
                findings.append(f"{path.relative_to(docs)}: missing Markdown target {target}")
        for target in WIKI_LINK.findall(text):
            if not wiki_target(path, target, docs, targets):
                findings.append(f"{path.relative_to(docs)}: missing or ambiguous wiki target {target}")
    return findings


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    findings = missing_links(root / "docs")
    if not findings:
        print("Documentation link check: all local links resolve.")
        return 0
    print("Documentation link check: unresolved or ambiguous links:")
    print("\n".join(f"  {finding}" for finding in findings))
    return 1


if __name__ == "__main__":
    sys.exit(main())
