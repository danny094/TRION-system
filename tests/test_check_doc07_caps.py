"""Regression tests for the canonical code-cap preflight."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts import check_code_caps, check_doc07_caps

EXPECTED_LINE_CAP = 200
EXPECTED_CODE_SUFFIXES = frozenset({".py", ".ts", ".tsx", ".js", ".css", ".html", ".sh"})


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(tmp_path: Path) -> Path:
    _git(["init"], tmp_path)
    _git(["config", "user.email", "test@example.com"], tmp_path)
    _git(["config", "user.name", "Test"], tmp_path)
    (tmp_path / "README.md").write_text("baseline\n", encoding="utf-8")
    _git(["add", "README.md"], tmp_path)
    _git(["commit", "-m", "baseline"], tmp_path)
    return tmp_path


def _write_lines(path: Path, count: int) -> None:
    path.write_text(
        "\n".join(f"line {number}" for number in range(count)) + "\n",
        encoding="utf-8",
    )


def _commit_file(repo: Path, name: str, count: int = 50) -> Path:
    path = repo / name
    _write_lines(path, count)
    _git(["add", name], repo)
    _git(["commit", "-m", f"add {name}"], repo)
    return path


def test_public_code_cap_contract_is_fixed():
    assert check_code_caps.LINE_CAP == EXPECTED_LINE_CAP
    assert check_code_caps.CODE_SUFFIXES == EXPECTED_CODE_SUFFIXES


def test_untracked_file_over_cap_is_violation(tmp_path):
    repo = _init_repo(tmp_path)
    _write_lines(repo / "new_module.py", check_code_caps.LINE_CAP + 1)

    assert check_code_caps.find_violations(repo) == [
        (Path("new_module.py"), 0, check_code_caps.LINE_CAP + 1)
    ]


def test_unstaged_and_staged_changes_are_both_checked(tmp_path):
    repo = _init_repo(tmp_path)
    unstaged = _commit_file(repo, "unstaged.py")
    staged = _commit_file(repo, "staged.py")
    _write_lines(unstaged, check_code_caps.LINE_CAP + 1)
    _write_lines(staged, check_code_caps.LINE_CAP + 1)
    _git(["add", "staged.py"], repo)

    assert check_code_caps.find_violations(repo) == [
        (Path("staged.py"), 50, check_code_caps.LINE_CAP + 1),
        (Path("unstaged.py"), 50, check_code_caps.LINE_CAP + 1),
    ]


def test_staged_violation_cannot_be_hidden_by_smaller_worktree_file(tmp_path):
    repo = _init_repo(tmp_path)
    target = _commit_file(repo, "staged.py")
    _write_lines(target, EXPECTED_LINE_CAP + 1)
    _git(["add", "staged.py"], repo)
    _write_lines(target, EXPECTED_LINE_CAP)

    assert check_code_caps.find_violations(repo) == [
        (Path("staged.py"), 50, EXPECTED_LINE_CAP + 1)
    ]


def test_exact_cap_and_all_current_code_suffixes_are_checked(tmp_path):
    repo = _init_repo(tmp_path)
    _write_lines(repo / "exact.py", EXPECTED_LINE_CAP)
    expected = {Path(f"large{suffix}") for suffix in EXPECTED_CODE_SUFFIXES}
    for path in expected:
        _write_lines(repo / path, EXPECTED_LINE_CAP + 1)
    _write_lines(repo / "notes.md", EXPECTED_LINE_CAP + 1)

    violations = check_code_caps.find_violations(repo)

    assert {path for path, _before, _after in violations} == expected


def test_deleted_code_file_is_not_a_false_positive(tmp_path):
    repo = _init_repo(tmp_path)
    deleted = _commit_file(repo, "deleted.py", check_code_caps.LINE_CAP + 1)
    deleted.unlink()

    assert check_code_caps.find_violations(repo) == []


def test_main_uses_the_mandatory_line_cap(tmp_path):
    repo = _init_repo(tmp_path)
    _write_lines(repo / "too_large.py", check_code_caps.LINE_CAP + 1)

    assert check_code_caps.main(repo) == 1


def test_legacy_facade_reexports_the_canonical_owner(tmp_path):
    repo = _init_repo(tmp_path)
    _write_lines(repo / "too_large.py", check_code_caps.LINE_CAP + 1)

    assert check_doc07_caps.main is check_code_caps.main
    assert check_doc07_caps.find_violations is check_code_caps.find_violations
    assert check_doc07_caps.main(repo) == 1


def test_legacy_command_remains_functional(tmp_path):
    repo = _init_repo(tmp_path)
    _write_lines(repo / "too_large.py", check_code_caps.LINE_CAP + 1)
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_doc07_caps.py"

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "too_large.py" in result.stdout


def test_legacy_command_exits_zero_when_clean(tmp_path):
    repo = _init_repo(tmp_path)
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_doc07_caps.py"

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
