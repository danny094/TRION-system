from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR_TREE = ROOT / "adapters" / "admin-api" / "vendor" / "container_commander"

EXPECTED_VENDOR_PY_FILES: set[str] = set()


def test_vendor_commander_tree_inventory_is_explicit_and_shrink_only():
    actual = {
        path.relative_to(VENDOR_TREE).as_posix()
        for path in VENDOR_TREE.rglob("*.py")
        if "__pycache__" not in path.parts
    }

    assert actual == EXPECTED_VENDOR_PY_FILES
