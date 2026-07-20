from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = [
    ROOT / "adapters",
    ROOT / "core",
    ROOT / "memory",
    ROOT / "utils",
    ROOT / "mcp-servers",
    ROOT / "examples",
]
EXCLUDED_PARTS = {
    "adapters/admin-api/vendor/container_commander",
    "mcp-servers/container-commander-old",
}
_BANNED_SNIPPETS = (
    "from container_commander",
    "import container_commander",
    "from vendor.container_commander",
    "import vendor.container_commander",
)


def _is_excluded(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(rel == prefix or rel.startswith(prefix + "/") for prefix in EXCLUDED_PARTS)


def test_repo_product_and_infra_code_has_no_direct_legacy_container_commander_imports():
    offenders: list[str] = []
    for scan_root in SCAN_ROOTS:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*.py")):
            if _is_excluded(path):
                continue
            rel = path.relative_to(ROOT)
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for snippet in _BANNED_SNIPPETS:
                    if snippet in stripped:
                        offenders.append(f"{rel}:{lineno}:{stripped}")

    assert offenders == []
