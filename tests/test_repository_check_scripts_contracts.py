"""Regression coverage for repository-script contracts and portable links."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_bundle_check_compares_generator_output_to_tracked_bundle_files():
    module = load_script("check_container_commander_bundle_freshness.py")
    expected = {Path("bundle_dispatch.py"): b"generated"}

    assert module.compare(expected, dict(expected)) == []
    assert module.compare(expected, {Path("bundle_dispatch.py"): b"drift"}) == [
        "content differs: bundle_dispatch.py"
    ]
    assert module.COMMITTED_BUNDLE == Path("examples/container_commander_bundle")


def test_bundle_check_reports_tracked_stale_generator_output(monkeypatch, tmp_path):
    module = load_script("check_container_commander_bundle_freshness.py")
    bundle = module.COMMITTED_BUNDLE
    stale = Path("bundle_generated_retired.py")
    stale_path = tmp_path / bundle / stale
    stale_path.parent.mkdir(parents=True)
    stale_path.write_bytes(b"retired")

    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=f"{bundle / stale}\n"),
    )

    expected, findings = module.tracked_generated_files(tmp_path, bundle, {})

    assert findings == []
    assert module.compare(expected, {}) == [f"missing generated file: {stale}"]


def test_doc_link_check_rejects_host_paths_and_checks_local_images(tmp_path):
    module = load_script("check_doc_links.py")
    docs = tmp_path / "docs"
    assets = docs / "assets"
    assets.mkdir(parents=True)
    (assets / "ok.svg").write_text("<svg/>", encoding="utf-8")
    host_target = tmp_path / "host-only.md"
    host_target.write_text("host specific", encoding="utf-8")
    page = docs / "page.md"
    page.write_text(
        f"![ok](assets/ok.svg)\n![missing](assets/missing.svg)\n[host]({host_target})\n",
        encoding="utf-8",
    )

    findings = module.missing_links(docs)

    assert "page.md: missing Markdown target assets/missing.svg" in findings
    assert f"page.md: missing Markdown target {host_target}" in findings


def test_doc_link_check_prefers_active_target_over_archive_copy(tmp_path):
    module = load_script("check_doc_links.py")
    docs = tmp_path / "docs"
    archive = docs / "archive" / "legacy"
    archive.mkdir(parents=True)
    stem = "README-freeze-status-2026-06-06"
    (docs / f"{stem}.md").write_text("root target\n", encoding="utf-8")
    (archive / f"{stem}.md").write_text("[broken](missing.md)\n", encoding="utf-8")
    (docs / "active.md").write_text(f"[[{stem}]]\n", encoding="utf-8")

    assert module.missing_links(docs) == []


def test_doc_link_check_rejects_missing_and_active_ambiguity(tmp_path):
    module = load_script("check_doc_links.py")
    docs = tmp_path / "docs"
    duplicate = docs / "duplicate"
    duplicate.mkdir(parents=True)
    (docs / "same.md").write_text("first\n", encoding="utf-8")
    (duplicate / "same.md").write_text("second\n", encoding="utf-8")
    (docs / "active.md").write_text("[[same]]\n[[missing]]\n", encoding="utf-8")

    findings = module.missing_links(docs)

    assert "active.md: missing or ambiguous wiki target same" in findings
    assert "active.md: missing or ambiguous wiki target missing" in findings


def test_deprecation_check_reports_only_actionable_markers(tmp_path):
    module = load_script("check_deprecation_deadlines.py")
    docs = tmp_path / "docs"
    core = tmp_path / "core"
    docs.mkdir()
    core.mkdir()
    (docs / "example.md").write_text(
        "`DEPRECATED 2099-12-31`\n```\nDEPRECATED 2020-01-01\n```\n",
        encoding="utf-8",
    )
    (core / "old.py").write_text("# DEPRECATED 2020-01-01\n", encoding="utf-8")

    assert module.findings(tmp_path, module.date(2026, 8, 16)) == [
        "core/old.py:1: expired on 2020-01-01"
    ]


def test_runtime_posture_reports_compose_facts_without_a_verdict(tmp_path):
    module = load_script("collect_runtime_posture.py")
    compose = tmp_path / "compose.yml"
    compose.write_text(
        "services:\n  app:\n    ports:\n      - '8080:8080'\n    volumes:\n"
        "      - '/host:/app'\n      - '/var/run/docker.sock:/var/run/docker.sock'\n",
        encoding="utf-8",
    )

    facts = module.compose_facts(compose)

    assert "port mapping: 8080:8080" in facts
    assert "docker socket mount: present" in facts


def test_pipeline_runner_uses_fixed_argv_and_propagates_all(monkeypatch, tmp_path, capsys):
    module = load_script("check_pipeline_contracts.py")
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout="REVIEW_REQUIRED keep me\n", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module.run_checks(tmp_path, include_all=True) == 0
    assert all(call[0][:2] == [module.sys.executable, "-B"] for call in calls)
    assert all("shell" not in call[1] for call in calls)
    assert [call[0][-1] for call in calls[:3]] == ["--all", "--all", "--all"]
    assert all(call[0][-1] != "--all" for call in calls[3:])
    assert capsys.readouterr().out.count("REVIEW_REQUIRED keep me") == len(calls)


def test_pipeline_runner_returns_nonzero_for_child_failure(monkeypatch, tmp_path, capsys):
    module = load_script("check_pipeline_contracts.py")

    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=7, stdout="child output\n", stderr="child error\n"),
    )

    assert module.run_checks(tmp_path, include_all=False) == 1
    output = capsys.readouterr().out
    assert "child output" in output
    assert "child error" in output
    assert "technical child failure" in output
