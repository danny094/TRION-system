#!/usr/bin/env python3
"""Prueft das 200-Zeilen-Cap aus docs/governance/07-design-rules.md.

Erfasst alle durch den aktuellen Working-Tree-Stand beruehrten *.py-Dateien
aus zwei Quellen:

- getrackte Aenderungen: `git diff --name-only`
- neue, noch ungetrackte Dateien: `git ls-files --others --exclude-standard`

Fuer jeden Treffer wird die Vorher-Zeilenzahl (Stand `HEAD`, 0 bei neuer
Datei) und die Nachher-Zeilenzahl (aktueller Working-Tree-Stand) ermittelt.
Verstoss = Nachher-Zeilenzahl > 200 -- unabhaengig davon, ob die Datei schon
vor der Aenderung ueber dem Cap lag. Kein Grandfathering, keine Ausnahme fuer
Testdateien (siehe docs/governance/38-non-coder-vetos.md).

Exit 0: alle beruehrten *.py-Dateien <= 200 Zeilen.
Exit 1: mindestens eine beruehrte *.py-Datei > 200 Zeilen.

Lauf gegen das echte Repo (vom Repo-Root):
    python3 scripts/check_doc07_caps.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LINE_CAP = 200


def _run_git(args: list[str], cwd: Path) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def tracked_changed_py_files(cwd: Path) -> list[str]:
    return [p for p in _run_git(["diff", "--name-only"], cwd) if p.endswith(".py")]


def untracked_new_py_files(cwd: Path) -> list[str]:
    paths = _run_git(["ls-files", "--others", "--exclude-standard"], cwd)
    return [p for p in paths if p.endswith(".py")]


def before_line_count(rel_path: str, cwd: Path) -> int:
    result = subprocess.run(
        ["git", "show", f"HEAD:{rel_path}"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return 0
    return len(result.stdout.splitlines())


def after_line_count(rel_path: str, cwd: Path) -> int:
    full_path = cwd / rel_path
    if not full_path.exists():
        return 0
    with full_path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def find_violations(cwd: Path, cap: int = LINE_CAP) -> list[tuple[str, int, int]]:
    """Liefert (Pfad, Vorher, Nachher) fuer jede beruehrte *.py-Datei > cap."""
    touched = sorted(set(tracked_changed_py_files(cwd)) | set(untracked_new_py_files(cwd)))
    violations = []
    for rel_path in touched:
        after = after_line_count(rel_path, cwd)
        if after > cap:
            before = before_line_count(rel_path, cwd)
            violations.append((rel_path, before, after))
    return violations


def main() -> int:
    cwd = Path.cwd()
    violations = find_violations(cwd)
    if not violations:
        print(f"Doc-07-Check: alle beruehrten *.py-Dateien <= {LINE_CAP} Zeilen.")
        return 0
    print(f"Doc-07-Check: {len(violations)} Verstoss/Verstoesse gegen {LINE_CAP}-Zeilen-Cap:")
    for rel_path, before, after in violations:
        print(f"  {rel_path}: vorher={before} nachher={after}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
