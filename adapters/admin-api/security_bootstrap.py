"""One-shot local writer for initial Admin and internal-caller auth material."""
from __future__ import annotations

import os
from pathlib import Path
import secrets
import sys

from security_auth import hash_credential
from security_contracts import BootstrapMaterial, BootstrapResult, SecurityPaths


class BootstrapConflict(RuntimeError):
    """Security material is only partially present or changed concurrently."""


def _write_new(path: Path, value: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o600)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def provision_security_material(
    paths: SecurityPaths,
    material: BootstrapMaterial,
) -> BootstrapResult:
    targets = (
        (paths.credential_hash, hash_credential(material.initial_password, salt=material.credential_salt).encode()),
        (paths.session_key, material.session_key),
        (paths.secret_resolve_token, material.secret_resolve_token.encode()),
        (paths.memory_read_token, material.memory_read_token.encode()),
        (paths.session_generation, b"0\n"),
    )
    present = tuple(path.exists() for path, _ in targets)
    if all(present):
        return BootstrapResult(False, None)
    if any(present):
        raise BootstrapConflict("partial security bootstrap state")

    created: list[Path] = []
    try:
        for path, value in targets:
            _write_new(path, value)
            created.append(path)
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    return BootstrapResult(True, material.initial_password)


def _random_material() -> BootstrapMaterial:
    return BootstrapMaterial(
        initial_password=secrets.token_urlsafe(24),
        credential_salt=secrets.token_bytes(16),
        session_key=secrets.token_bytes(32),
        secret_resolve_token=secrets.token_urlsafe(32),
        memory_read_token=secrets.token_urlsafe(32),
    )


def main() -> int:
    try:
        result = provision_security_material(SecurityPaths.from_config(), _random_material())
    except BootstrapConflict:
        print("Security bootstrap blocked: partial material exists.", file=sys.stderr)
        return 2
    except OSError:
        print("Security bootstrap failed: material could not be written.", file=sys.stderr)
        return 3
    if result.initial_password is not None:
        print(result.initial_password)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
