"""Regression coverage for changed-file repository preflight scripts."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("script_name", "function_name"),
    [
        ("check_code_caps.py", "changed_code_paths"),
        ("check_import_boundaries.py", "changed_python_paths"),
        ("check_prompt_provenance_report.py", "changed_paths"),
    ],
)
def test_changed_file_checks_include_staged_only_paths(monkeypatch, tmp_path, script_name, function_name):
    module = load_script(script_name)
    calls = []
    staged_path = tmp_path / "core" / "staged_only.py"
    staged_path.parent.mkdir()
    staged_path.write_text("pass\n", encoding="utf-8")

    def fake_git_paths(args, _root):
        calls.append(args)
        return {Path("core/staged_only.py")} if "--cached" in args else set()

    monkeypatch.setattr(module, "git_paths", fake_git_paths)

    assert getattr(module, function_name)(tmp_path) == [Path("core/staged_only.py")]
    assert ["diff", "--cached", "--name-only"] in calls


def test_import_boundaries_reject_mcp_server_and_relative_root_bypasses(tmp_path):
    module = load_script("check_import_boundaries.py")
    server_path = tmp_path / "mcp-servers" / "demo" / "server.py"
    utils_path = tmp_path / "utils" / "helper.py"
    config_path = tmp_path / "config" / "loader.py"
    server_path.parent.mkdir(parents=True)
    utils_path.parent.mkdir(parents=True)
    config_path.parent.mkdir(parents=True)
    server_path.write_text("from core import secrets\n", encoding="utf-8")
    utils_path.write_text("from ..core import secrets\n", encoding="utf-8")
    config_path.write_text("from intelligence_modules import catalog\n", encoding="utf-8")

    server_findings = module.violations_for(server_path.relative_to(tmp_path), tmp_path)
    utils_findings = module.violations_for(utils_path.relative_to(tmp_path), tmp_path)
    config_findings = module.violations_for(config_path.relative_to(tmp_path), tmp_path)

    assert server_findings == ["mcp-servers/demo/server.py:1: mcp-servers must not import core"]
    assert utils_findings == ["utils/helper.py:1: utils must not import core"]
    assert config_findings == ["config/loader.py:1: config must not import intelligence_modules"]


def test_core_allows_only_absolute_cim_skill_rag_loader_imports(tmp_path):
    module = load_script("check_import_boundaries.py")
    loader_path = tmp_path / "core" / "loader.py"
    blocked_path = tmp_path / "core" / "blocked.py"
    relative_path = tmp_path / "core" / "routing" / "relative.py"
    loader_path.parent.mkdir(parents=True)
    relative_path.parent.mkdir(parents=True)
    loader_path.write_text(
        "from intelligence_modules.cim_skill_rag.meaning_concept_loader import load\n",
        encoding="utf-8",
    )
    blocked_path.write_text("from intelligence_modules.prompt_manager import load_prompt\n", encoding="utf-8")
    relative_path.write_text(
        "from ...intelligence_modules.cim_skill_rag.meaning_concept_loader import load\n",
        encoding="utf-8",
    )

    assert module.violations_for(loader_path.relative_to(tmp_path), tmp_path) == []
    assert module.violations_for(blocked_path.relative_to(tmp_path), tmp_path) == [
        "core/blocked.py:1: core must not import intelligence_modules"
    ]
    assert module.violations_for(relative_path.relative_to(tmp_path), tmp_path) == [
        "core/routing/relative.py:1: core must not import intelligence_modules"
    ]


def test_shadow_authority_changed_scope_includes_examples_and_mcp_servers(monkeypatch, tmp_path):
    module = load_script("check_shadow_authorities.py")
    expected = {Path("examples/demo.py"), Path("mcp-servers/demo/server.py")}
    for path in expected:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("pass\n", encoding="utf-8")

    monkeypatch.setattr(module, "git_paths", lambda _args, _root: expected)

    assert module.changed_paths(tmp_path) == sorted(expected)


def test_shadow_authority_changed_scope_unions_all_git_sources(monkeypatch, tmp_path):
    module = load_script("check_shadow_authorities.py")
    expected_calls = [
        ["diff", "--name-only"],
        ["diff", "--cached", "--name-only"],
        ["ls-files", "--others", "--exclude-standard"],
    ]
    paths_by_call = {
        tuple(expected_calls[0]): Path("core/unstaged.py"),
        tuple(expected_calls[1]): Path("examples/staged.py"),
        tuple(expected_calls[2]): Path("mcp-servers/demo/untracked.py"),
    }
    calls = []
    for path in paths_by_call.values():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("pass\n", encoding="utf-8")

    def fake_git_paths(args, _root):
        calls.append(args)
        return {paths_by_call[tuple(args)]}

    monkeypatch.setattr(module, "git_paths", fake_git_paths)
    assert module.changed_paths(tmp_path) == sorted(paths_by_call.values())
    assert calls == expected_calls


def test_shadow_authority_all_scope_uses_tracked_existing_code(monkeypatch, tmp_path):
    module = load_script("check_shadow_authorities.py")
    tracked = Path("core/tracked.py")
    untracked = Path("mcp/untracked.py")
    outside_root = Path("docs/ignored.py")
    for path in (tracked, untracked, outside_root):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("pass\n", encoding="utf-8")
    calls = []

    def fake_git_paths(args, _root):
        calls.append(args)
        return {tracked, outside_root, Path("mcp/missing.py")}

    monkeypatch.setattr(module, "git_paths", fake_git_paths)
    assert module.all_paths(tmp_path) == [tracked]
    assert untracked not in module.all_paths(tmp_path)
    assert calls == [["ls-files"], ["ls-files"]]
