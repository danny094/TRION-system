from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR_TREE = ROOT / "adapters" / "admin-api" / "vendor" / "container_commander"


def test_vendor_commander_tree_has_no_local_function_or_class_definitions():
    offenders: list[str] = []
    for path in sorted(VENDOR_TREE.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("def ") or stripped.startswith("class "):
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}:{stripped}")

    assert offenders == []
