"""Tests fuer scripts/check_doc07_caps.py (W1 SP2).

Deckt beide Quellen beruehrter *.py-Dateien ab: getrackte Aenderungen
(`git diff --name-only`) und neue, ungetrackte Dateien
(`git ls-files --others --exclude-standard`). Kein Grandfathering: der
Nachher-Stand entscheidet, unabhaengig vom Vorher-Stand. Keine Ausnahme fuer
Testdateien.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.check_doc07_caps import LINE_CAP, find_violations


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(tmp_path: Path) -> Path:
    _git(["init"], tmp_path)
    _git(["config", "user.email", "test@example.com"], tmp_path)
    _git(["config", "user.name", "Test"], tmp_path)
    (tmp_path / "README.md").write_text("baseline\n")
    _git(["add", "README.md"], tmp_path)
    _git(["commit", "-m", "baseline"], tmp_path)
    return tmp_path


def _write_lines(path: Path, n: int) -> None:
    path.write_text("\n".join(f"# line {i}" for i in range(n)) + "\n")


def test_tracked_change_over_cap_is_violation(tmp_path):
    repo = _init_repo(tmp_path)
    target = repo / "module.py"
    _write_lines(target, 50)
    _git(["add", "module.py"], repo)
    _git(["commit", "-m", "add module"], repo)

    _write_lines(target, LINE_CAP + 1)

    violations = find_violations(repo)

    assert len(violations) == 1
    path, before, after = violations[0]
    assert path == "module.py"
    assert before == 50
    assert after == LINE_CAP + 1


def test_untracked_new_file_over_cap_is_violation(tmp_path):
    repo = _init_repo(tmp_path)

    new_file = repo / "new_module.py"
    _write_lines(new_file, LINE_CAP + 1)

    violations = find_violations(repo)

    assert len(violations) == 1
    path, before, after = violations[0]
    assert path == "new_module.py"
    assert before == 0
    assert after == LINE_CAP + 1


def test_all_files_within_cap_is_clean(tmp_path):
    repo = _init_repo(tmp_path)
    tracked = repo / "module.py"
    _write_lines(tracked, 50)
    _git(["add", "module.py"], repo)
    _git(["commit", "-m", "add module"], repo)
    _write_lines(tracked, LINE_CAP)

    new_file = repo / "new_module.py"
    _write_lines(new_file, LINE_CAP)

    violations = find_violations(repo)

    assert violations == []


def test_no_exception_for_test_files_over_cap(tmp_path):
    repo = _init_repo(tmp_path)
    test_file = repo / "test_something.py"
    _write_lines(test_file, LINE_CAP + 1)

    violations = find_violations(repo)

    assert len(violations) == 1
    assert violations[0][0] == "test_something.py"


def test_non_py_files_are_ignored(tmp_path):
    repo = _init_repo(tmp_path)
    _write_lines(repo / "notes.md", LINE_CAP + 5)

    violations = find_violations(repo)

    assert violations == []


def test_cli_exit_code_nonzero_on_violation(tmp_path):
    repo = _init_repo(tmp_path)
    new_file = repo / "new_module.py"
    _write_lines(new_file, LINE_CAP + 1)

    script = Path(__file__).resolve().parents[1] / "scripts" / "check_doc07_caps.py"
    result = subprocess.run([sys.executable, str(script)], cwd=repo, capture_output=True, text=True)

    assert result.returncode == 1
    assert "new_module.py" in result.stdout


def test_cli_exit_code_zero_when_clean(tmp_path):
    repo = _init_repo(tmp_path)

    script = Path(__file__).resolve().parents[1] / "scripts" / "check_doc07_caps.py"
    result = subprocess.run([sys.executable, str(script)], cwd=repo, capture_output=True, text=True)

    assert result.returncode == 0
