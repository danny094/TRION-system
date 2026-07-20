from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def test_admin_api_product_code_has_no_sys_path_injection():
    offenders: list[str] = []
    for path in sorted(ADMIN_API_DIR.rglob("*.py")):
        rel = path.relative_to(ROOT)
        source = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), start=1):
            if "sys.path.insert" in line:
                offenders.append(f"{rel}:{lineno}:{line.strip()}")

    assert offenders == []
