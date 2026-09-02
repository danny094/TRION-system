from __future__ import annotations

import logging
from pathlib import Path
import stat
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API = ROOT / "adapters" / "admin-api"
if str(ADMIN_API) not in sys.path:
    sys.path.insert(0, str(ADMIN_API))

import security_bootstrap
from security_auth import SecurityAuthority
from security_bootstrap import BootstrapConflict, provision_security_material
from security_contracts import BootstrapMaterial, PrincipalKind, SecurityPaths


def _paths(tmp_path: Path) -> SecurityPaths:
    return SecurityPaths(
        credential_hash=tmp_path / "admin" / "credential.hash",
        session_key=tmp_path / "admin" / "session.key",
        secret_resolve_token=tmp_path / "resolve-volume" / "token",
        memory_read_token=tmp_path / "memory-volume" / "token",
    )


def _material(suffix: str = "one") -> BootstrapMaterial:
    return BootstrapMaterial(
        initial_password=f"TEST-ONLY-password-{suffix}",
        credential_salt=f"TEST-ONLY-salt-{suffix}".encode().ljust(16, b"x"),
        session_key=f"TEST-ONLY-session-{suffix}".encode().ljust(32, b"x"),
        secret_resolve_token=f"TEST-ONLY-resolve-{suffix}",
        memory_read_token=f"TEST-ONLY-memory-{suffix}",
    )


def _snapshot(paths: SecurityPaths) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in paths.material_paths()}


def test_real_security_authority_binds_bootstrap_material_fail_closed(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    material = _material("authority")
    provision_security_material(paths, material)
    authority = SecurityAuthority(paths, ttl_seconds=60)

    assert authority.is_provisioned() is True
    assert authority.verify_password(material.initial_password) is True
    assert authority.verify_password("TEST-ONLY-wrong") is False
    issued = authority.issue_session()
    assert authority.authenticate_session(issued.token).kind is PrincipalKind.BROWSER
    assert authority.authenticate_service(material.secret_resolve_token).kind is PrincipalKind.SECRET_RESOLVE
    assert authority.authenticate_service(material.memory_read_token).kind is PrincipalKind.MEMORY_READ
    assert authority.authenticate_service("TEST-ONLY-wrong") is None

    paths.memory_read_token.write_text("", encoding="utf-8")
    assert authority.is_provisioned() is False
    assert authority.authenticate_service(material.memory_read_token) is None
    paths.session_key.write_bytes(b"")
    assert authority.authenticate_session(issued.token) is None


def test_bootstrap_creates_four_separate_restrictive_materials_without_logs(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _paths(tmp_path)
    material = _material()

    with caplog.at_level(logging.DEBUG):
        result = provision_security_material(paths, material)

    assert result.created is True
    assert result.initial_password == material.initial_password
    assert len(paths.material_paths()) == 4
    assert all(path.is_file() for path in paths.material_paths())
    assert paths.secret_resolve_token.parent != paths.memory_read_token.parent
    assert paths.credential_hash.read_text(encoding="utf-8") != material.initial_password
    assert paths.session_key.read_bytes() == material.session_key
    assert paths.secret_resolve_token.read_text(encoding="utf-8") == material.secret_resolve_token
    assert paths.memory_read_token.read_text(encoding="utf-8") == material.memory_read_token
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in paths.material_paths())
    assert paths.session_generation.read_text(encoding="ascii") == "0\n"
    assert stat.S_IMODE(paths.session_generation.stat().st_mode) == 0o600

    captured = capsys.readouterr()
    observable = captured.out + captured.err + caplog.text
    for forbidden in (
        material.initial_password,
        material.secret_resolve_token,
        material.memory_read_token,
        material.session_key.decode(),
    ):
        assert forbidden not in observable


def test_bootstrap_repeat_preserves_bytes_and_never_reemits_credential(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    first = provision_security_material(paths, _material("first"))
    before = _snapshot(paths)

    repeated = provision_security_material(paths, _material("replacement"))

    assert first.initial_password == "TEST-ONLY-password-first"
    assert repeated.created is False
    assert repeated.initial_password is None
    assert _snapshot(paths) == before


def test_bootstrap_refuses_partial_state_without_creating_or_overwriting(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths.credential_hash.parent.mkdir(parents=True)
    paths.credential_hash.write_bytes(b"pre-existing-test-marker")

    with pytest.raises(BootstrapConflict):
        provision_security_material(paths, _material())

    assert paths.credential_hash.read_bytes() == b"pre-existing-test-marker"
    assert not paths.session_key.exists()
    assert not paths.secret_resolve_token.exists()
    assert not paths.memory_read_token.exists()
    assert not paths.session_generation.exists()


def test_bootstrap_write_failure_removes_every_file_created_by_the_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)
    original = security_bootstrap._write_new
    calls = 0

    def fail_second(path: Path, value: bytes) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("TEST-ONLY-injected-write-failure")
        original(path, value)

    monkeypatch.setattr(security_bootstrap, "_write_new", fail_second)
    with pytest.raises(OSError, match="TEST-ONLY"):
        provision_security_material(paths, _material())

    assert not any(path.exists() for path in (*paths.material_paths(), paths.session_generation))


def test_bootstrap_cli_prints_only_first_password_and_repeat_is_silent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _paths(tmp_path)
    material = _material("cli")
    monkeypatch.setattr(SecurityPaths, "from_config", classmethod(lambda cls: paths))
    monkeypatch.setattr(security_bootstrap, "_random_material", lambda: material)

    assert security_bootstrap.main() == 0
    first = capsys.readouterr()
    assert first.out == f"{material.initial_password}\n"
    assert first.err == ""
    assert material.secret_resolve_token not in first.out
    assert material.memory_read_token not in first.out

    assert security_bootstrap.main() == 0
    repeated = capsys.readouterr()
    assert repeated.out == ""
    assert repeated.err == ""


def test_bootstrap_cli_uses_fixed_failure_codes_without_path_or_secret_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _paths(tmp_path)
    paths.credential_hash.parent.mkdir(parents=True)
    paths.credential_hash.write_text("TEST-ONLY-partial", encoding="utf-8")
    monkeypatch.setattr(SecurityPaths, "from_config", classmethod(lambda cls: paths))

    assert security_bootstrap.main() == 2
    conflict = capsys.readouterr()
    assert conflict.out == ""
    assert conflict.err == "Security bootstrap blocked: partial material exists.\n"

    def fail_write(*args, **kwargs):
        raise OSError("/TEST-ONLY/private/path")

    monkeypatch.setattr(security_bootstrap, "provision_security_material", fail_write)
    assert security_bootstrap.main() == 3
    failed = capsys.readouterr()
    assert failed.out == ""
    assert failed.err == "Security bootstrap failed: material could not be written.\n"
