from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_local_graph_builders_tree_is_removed() -> None:
    assert not (REPO_ROOT / "intelligence_modules" / "local_graph_builders").exists()


def test_container_commander_old_tree_is_removed_from_mcp_servers() -> None:
    assert not (REPO_ROOT / "mcp-servers" / "container-commander-old").exists()


def test_admin_api_dockerfile_no_longer_bakes_vendorized_container_commander_runtime() -> None:
    dockerfile = (REPO_ROOT / "adapters" / "admin-api" / "Dockerfile").read_text()
    assert "COPY adapters/admin-api/vendor/container_commander /app/container_commander" not in dockerfile
    assert 'ENV PYTHONPATH="/app:/app/container_commander"' not in dockerfile
    assert "mcp-servers/container-commander-old" not in dockerfile
