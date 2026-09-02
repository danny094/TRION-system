"""Static P16-SP1 ingress and token-recipient contracts for root Compose."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from config.infra.cors import get_allowed_origins


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"
ADMIN_DOCKERFILE = ROOT / "adapters/admin-api/Dockerfile"
SECURITY_CONTRACTS = ROOT / "adapters/admin-api/security_contracts.py"
SECRET_VOLUME = "trion-secret-resolve-token"
MEMORY_VOLUME = "trion-memory-read-token"


def _compose_text() -> str:
    return COMPOSE.read_text(encoding="utf-8")


def _service(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(name)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_.-]+:\n|^volumes:\n|\Z)",
        text,
    )
    assert match is not None, f"missing Compose service: {name}"
    return match.group("body")


def _subsection(service: str, key: str) -> str:
    match = re.search(
        rf"(?ms)^    {re.escape(key)}:\s*\n(?P<body>.*?)(?=^    [A-Za-z0-9_.-]+:|\Z)",
        service,
    )
    return match.group("body") if match else ""


def _mount_lines(service: str) -> list[str]:
    return [line.strip().removeprefix("- ") for line in _subsection(service, "volumes").splitlines()]


def _mount(service: str, volume: str) -> str:
    matches = [line for line in _mount_lines(service) if line.startswith(f"{volume}:")]
    assert len(matches) == 1, f"expected one {volume} mount, found {matches}"
    return matches[0]


def _dockerfile_copy_sources() -> tuple[Path, ...]:
    sources = []
    for line in ADMIN_DOCKERFILE.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "COPY":
            sources.append(ROOT / parts[1])
    return tuple(sources)


def _local_security_contract_imports() -> tuple[Path, ...]:
    tree = ast.parse(SECURITY_CONTRACTS.read_text(encoding="utf-8"))
    return tuple(sorted({
        ROOT / f"{node.module.replace('.', '/')}.py"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and (ROOT / f"{node.module.replace('.', '/')}.py").is_file()
    }))


def test_admin_image_materializes_local_security_contract_imports() -> None:
    local_imports = _local_security_contract_imports()
    copy_sources = _dockerfile_copy_sources()

    missing = [
        path.relative_to(ROOT).as_posix()
        for path in sorted(local_imports)
        if not any(path.is_relative_to(source) for source in copy_sources)
    ]
    assert missing == [], f"local security imports missing from admin image: {missing}"


def test_admin_runtime_mounts_do_not_shadow_security_import_roots() -> None:
    admin = _service(_compose_text(), "trion-admin-api")
    mount_targets = {
        line.split(":", maxsplit=1)[1].removesuffix(":ro")
        for line in _mount_lines(admin)
    }
    import_roots = {
        f"/app/{path.relative_to(ROOT).parts[0]}"
        for path in _local_security_contract_imports()
    }

    assert mount_targets.isdisjoint(import_roots)
    assert _mount(admin, "trion-memory-files") == "trion-memory-files:/app/protocol_memory"
    assert "PROTOCOL_DIR: /app/protocol_memory" in _subsection(admin, "environment")


def test_only_loopback_browser_ingress_and_no_memory_port() -> None:
    text = _compose_text()
    memory = _service(text, "trion-memory")
    admin = _service(text, "trion-admin-api")
    webui = _service(text, "trion-webui")

    assert _subsection(memory, "ports") == ""
    assert _subsection(memory, "network_mode") == ""
    assert _subsection(admin, "network_mode") == ""
    assert _subsection(webui, "network_mode") == ""
    assert _subsection(admin, "ports").count("- ") == 1
    assert _subsection(webui, "ports").count("- ") == 1
    assert '127.0.0.1:${ADMIN_API_PORT:-8200}:8200' in _subsection(admin, "ports")
    assert '127.0.0.1:${WEBUI_PORT:-3000}:3000' in _subsection(webui, "ports")


def test_bootstrap_profile_owns_both_writable_token_volumes() -> None:
    text = _compose_text()
    bootstrap = _service(text, "trion-security-bootstrap")

    assert "profiles:" in bootstrap and "bootstrap" in bootstrap
    assert 'command: ["python", "-B", "security_bootstrap.py"]' in bootstrap
    assert 'TRION_SECURITY_BOOTSTRAP_MODE: "true"' in bootstrap
    for volume in (SECRET_VOLUME, MEMORY_VOLUME):
        mount = _mount(bootstrap, volume)
        assert not mount.endswith(":ro")


def test_runtime_recipients_are_minimal_and_read_only() -> None:
    text = _compose_text()
    admin = _service(text, "trion-admin-api")
    memory = _service(text, "trion-memory")

    assert _mount(admin, SECRET_VOLUME).endswith(":ro")
    assert _mount(admin, MEMORY_VOLUME).endswith(":ro")
    assert _mount(memory, MEMORY_VOLUME).endswith(":ro")
    assert SECRET_VOLUME not in _subsection(memory, "volumes")
    for service_name in re.findall(r"(?m)^  ([A-Za-z0-9_.-]+):\s*$", text.split("\nvolumes:\n", 1)[0]):
        if service_name in {"trion-admin-api", "trion-memory", "trion-security-bootstrap"}:
            continue
        volumes = _subsection(_service(text, service_name), "volumes")
        assert SECRET_VOLUME not in volumes
        assert MEMORY_VOLUME not in volumes


def test_token_volumes_exist_without_environment_token_values() -> None:
    text = _compose_text()
    volumes = text.split("\nvolumes:\n", maxsplit=1)[1]

    assert re.search(rf"(?m)^  {SECRET_VOLUME}:\s*$", volumes)
    assert re.search(rf"(?m)^  {MEMORY_VOLUME}:\s*$", volumes)
    for service_name in ("trion-security-bootstrap", "trion-admin-api", "trion-memory"):
        environment = _subsection(_service(text, service_name), "environment")
        assert "INTERNAL_SECRET_RESOLVE_TOKEN" not in environment
        assert re.search(r"(?mi)^\s*MEMORY_READ_TOKEN\s*:", environment) is None
        assert re.search(r"\$\{[^}]*TOKEN[^}]*\}", environment) is None


def test_credentialed_cors_has_no_wildcard_origin() -> None:
    admin = _service(_compose_text(), "trion-admin-api")
    environment = _subsection(admin, "environment")

    assert 'ALLOWED_ORIGINS: "*"' not in environment
    assert "TRION_ALLOWED_ORIGINS: '*'" not in environment


def test_cors_rejects_nonlocal_or_ambiguous_configured_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for invalid in ("*", "https://attacker.invalid", "http://localhost.evil:3000", "http://localhost"):
        monkeypatch.setenv("TRION_ALLOWED_ORIGINS", invalid)
        with pytest.raises(ValueError, match="local HTTP"):
            get_allowed_origins()

    monkeypatch.setenv("TRION_ALLOWED_ORIGINS", "http://localhost:3001,http://127.0.0.1:3001")
    assert get_allowed_origins() == ("http://localhost:3001", "http://127.0.0.1:3001")
