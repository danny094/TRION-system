from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR_README = ROOT / "adapters" / "admin-api" / "vendor" / "container_commander" / "README.md"
LEGACY_SHIMS_DOC = ROOT / "docs" / "archive" / "legacy" / "12-legacy-import-shims-admin-webui.md"


def test_vendor_commander_readme_describes_compat_only_state():
    source = VENDOR_README.read_text(encoding="utf-8")

    assert "compat-only" in source
    assert "keine eigene Produktlogik" in source
    assert "nicht Teil des Runtime-Images" in source
    assert "Alle Shims wurden entfernt" not in source
    assert "Container Commander — MCP Server" not in source


def test_legacy_shims_doc_no_longer_claims_old_container_commander_pythonpath_runtime():
    source = LEGACY_SHIMS_DOC.read_text(encoding="utf-8")

    assert 'ENV PYTHONPATH="/app:/app/container_commander"' not in source
    assert "COPY mcp-servers/container-commander /app/container_commander" not in source
    assert 'ENV PYTHONPATH="/app"' in source
    assert "`vendor/container_commander` wird nicht mehr ins Runtime-Image" in source
