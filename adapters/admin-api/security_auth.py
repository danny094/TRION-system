"""Credential, signed-session and installed-token verification authority."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import time

from security_contracts import (
    AuthenticatedPrincipal,
    IssuedSession,
    PrincipalKind,
    SecurityPaths,
    SessionClaims,
)


_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


class SessionRejected(ValueError):
    """A session is malformed, forged, expired or revoked."""


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if _b64encode(decoded) != value:
        raise ValueError("non-canonical encoding")
    return decoded


def hash_credential(password: str, *, salt: bytes) -> str:
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64encode(salt)}${_b64encode(digest)}"


def verify_credential(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = encoded.strip().split("$", 5)
        if scheme != "scrypt" or (int(n), int(r), int(p)) != (_SCRYPT_N, _SCRYPT_R, _SCRYPT_P):
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=_b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32
        )
        return hmac.compare_digest(actual, _b64decode(expected))
    except (TypeError, ValueError):
        return False


class SessionCodec:
    def __init__(self, *, signing_key: bytes, ttl_seconds: int) -> None:
        if len(signing_key) < 16 or ttl_seconds <= 0:
            raise ValueError("invalid session configuration")
        self._key = signing_key
        self._ttl = ttl_seconds

    def _csrf(self, subject: str, generation: int, nonce: str) -> str:
        value = f"csrf:{subject}:{generation}:{nonce}".encode("utf-8")
        return _b64encode(hmac.new(self._key, value, hashlib.sha256).digest())

    def issue(self, subject: str, generation: int, now: int, nonce: str) -> IssuedSession:
        expires = int(now) + self._ttl
        payload = json.dumps(
            {"sub": subject, "gen": generation, "exp": expires, "nonce": nonce},
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        encoded = _b64encode(payload)
        signature = _b64encode(hmac.new(self._key, encoded.encode("ascii"), hashlib.sha256).digest())
        return IssuedSession(f"{encoded}.{signature}", self._csrf(subject, generation, nonce), expires)

    def verify(self, token: str, generation: int, now: int) -> SessionClaims:
        try:
            encoded, supplied = token.split(".", 1)
            expected = hmac.new(self._key, encoded.encode("ascii"), hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _b64decode(supplied)):
                raise SessionRejected("signature")
            data = json.loads(_b64decode(encoded))
            subject, nonce = str(data["sub"]), str(data["nonce"])
            token_generation, expires = int(data["gen"]), int(data["exp"])
            if not subject or token_generation != generation or int(now) >= expires:
                raise SessionRejected("claims")
            return SessionClaims(subject, token_generation, self._csrf(subject, token_generation, nonce), expires)
        except SessionRejected:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise SessionRejected("malformed") from exc


def _read_nonempty(path: Path, *, binary: bool = False) -> str | bytes:
    value = path.read_bytes() if binary else path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError("empty security material")
    return value


class SecurityAuthority:
    def __init__(self, paths: SecurityPaths, ttl_seconds: int) -> None:
        self.paths = paths
        self.ttl_seconds = ttl_seconds

    def is_provisioned(self) -> bool:
        paths = (*self.paths.material_paths(), self.paths.session_generation)
        try:
            return all(path.is_file() and path.stat().st_size > 0 for path in paths)
        except OSError:
            return False

    def verify_password(self, password: str) -> bool:
        try:
            return verify_credential(password, str(_read_nonempty(self.paths.credential_hash)))
        except (OSError, ValueError):
            return False

    def _generation(self) -> int:
        return int(_read_nonempty(self.paths.session_generation))

    def _codec(self) -> SessionCodec:
        return SessionCodec(signing_key=bytes(_read_nonempty(self.paths.session_key, binary=True)), ttl_seconds=self.ttl_seconds)

    def issue_session(self) -> IssuedSession:
        nonce = _b64encode(os.urandom(24))
        return self._codec().issue("admin", self._generation(), int(time.time()), nonce)

    def authenticate_session(self, token: str) -> AuthenticatedPrincipal | None:
        try:
            claims = self._codec().verify(token, self._generation(), int(time.time()))
            return AuthenticatedPrincipal(claims.subject, PrincipalKind.BROWSER, claims.csrf_token, claims.expires_at)
        except (OSError, ValueError, SessionRejected):
            return None

    def authenticate_service(self, token: str) -> AuthenticatedPrincipal | None:
        for path, kind in (
            (self.paths.secret_resolve_token, PrincipalKind.SECRET_RESOLVE),
            (self.paths.memory_read_token, PrincipalKind.MEMORY_READ),
        ):
            try:
                if hmac.compare_digest(token, str(_read_nonempty(path))):
                    return AuthenticatedPrincipal(kind.value, kind)
            except (OSError, ValueError):
                continue
        return None

    def revoke_sessions(self) -> None:
        value = f"{self._generation() + 1}\n".encode("ascii")
        temporary = self.paths.session_generation.with_suffix(".tmp")
        temporary.write_bytes(value)
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.paths.session_generation)
