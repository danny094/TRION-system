"""Shared contracts for the single Admin API authentication authority."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from config.infra.security import SECRET_RESOLVE_ROUTE_PREFIX
from memory.embedding.config import MEMORY_READ_ROUTES


class PrincipalKind(str, Enum):
    BROWSER = "browser"
    SECRET_RESOLVE = "secret_resolve"
    MEMORY_READ = "memory_read"


@dataclass(frozen=True)
class ServiceRouteContract:
    principal_kind: PrincipalKind
    method: str
    exact_paths: frozenset[str] = frozenset()
    path_prefix: str | None = None

    def matches_path(self, path: str) -> bool:
        if self.path_prefix is None:
            return path in self.exact_paths
        suffix = path[len(self.path_prefix) :] if path.startswith(self.path_prefix) else ""
        return bool(suffix) and "/" not in suffix

    def allows(self, method: str, path: str) -> bool:
        return method == self.method and self.matches_path(path)


SECRET_RESOLVE_ROUTE_CONTRACT = ServiceRouteContract(
    principal_kind=PrincipalKind.SECRET_RESOLVE,
    method="GET",
    path_prefix=f"{SECRET_RESOLVE_ROUTE_PREFIX}/",
)
MEMORY_READ_ROUTE_CONTRACT = ServiceRouteContract(
    principal_kind=PrincipalKind.MEMORY_READ,
    method="GET",
    exact_paths=MEMORY_READ_ROUTES,
)
SERVICE_ROUTE_CONTRACTS = {
    contract.principal_kind: contract
    for contract in (SECRET_RESOLVE_ROUTE_CONTRACT, MEMORY_READ_ROUTE_CONTRACT)
}


def service_route_allowed(kind: PrincipalKind, method: str, path: str) -> bool:
    contract = SERVICE_ROUTE_CONTRACTS.get(kind)
    return contract.allows(method, path) if contract is not None else False


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    subject: str
    kind: PrincipalKind
    csrf_token: str | None = None
    expires_at: int | None = None


@dataclass(frozen=True)
class MiddlewareConfig:
    cookie_name: str
    csrf_header_name: str
    allowed_origins: tuple[str, ...]
    cookie_secure: bool = False


@dataclass(frozen=True)
class SecurityPaths:
    credential_hash: Path
    session_key: Path
    secret_resolve_token: Path
    memory_read_token: Path

    @property
    def session_generation(self) -> Path:
        return self.credential_hash.with_name("session.generation")

    def material_paths(self) -> tuple[Path, Path, Path, Path]:
        return (
            self.credential_hash,
            self.session_key,
            self.secret_resolve_token,
            self.memory_read_token,
        )

    @classmethod
    def from_config(cls) -> "SecurityPaths":
        from config.infra.security import (
            get_admin_credential_hash_path,
            get_admin_session_key_path,
            get_memory_read_token_path,
            get_secret_resolve_token_path,
        )

        return cls(
            credential_hash=get_admin_credential_hash_path(),
            session_key=get_admin_session_key_path(),
            secret_resolve_token=get_secret_resolve_token_path(),
            memory_read_token=get_memory_read_token_path(),
        )


@dataclass(frozen=True)
class BootstrapMaterial:
    initial_password: str
    credential_salt: bytes
    session_key: bytes
    secret_resolve_token: str
    memory_read_token: str


@dataclass(frozen=True)
class BootstrapResult:
    created: bool
    initial_password: str | None


@dataclass(frozen=True)
class IssuedSession:
    token: str
    csrf_token: str
    expires_at: int


@dataclass(frozen=True)
class SessionClaims:
    subject: str
    generation: int
    csrf_token: str
    expires_at: int
