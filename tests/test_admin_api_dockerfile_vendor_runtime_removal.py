from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "adapters" / "admin-api" / "Dockerfile"


def test_admin_api_dockerfile_uses_plain_app_pythonpath_without_vendor_runtime():
    source = DOCKERFILE.read_text(encoding="utf-8")

    assert 'ENV PYTHONPATH="/app"' in source
    assert "/app/container_commander" not in source
    assert "COPY adapters/admin-api/vendor/container_commander /app/container_commander" not in source
