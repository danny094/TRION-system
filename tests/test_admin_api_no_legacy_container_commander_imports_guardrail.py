from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"

_BANNED_SNIPPETS = (
    "from container_commander",
    "import container_commander",
    "from vendor.container_commander",
    "import vendor.container_commander",
)


def test_admin_api_product_code_has_no_direct_legacy_container_commander_imports():
    offenders: list[str] = []
    for path in sorted(ADMIN_API_DIR.rglob("*.py")):
        rel = path.relative_to(ROOT)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for snippet in _BANNED_SNIPPETS:
                if snippet in stripped:
                    offenders.append(f"{rel}:{lineno}:{stripped}")

    assert offenders == []
