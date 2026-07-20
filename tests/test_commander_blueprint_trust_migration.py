from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"
DEPLOY_TRUST_PATH = ADMIN_API_DIR / "commander_deploy_trust.py"
GRAPH_SYNC_PATH = ADMIN_API_DIR / "commander_blueprint_graph_sync.py"
LOCAL_TRUST_PATH = ADMIN_API_DIR / "commander_blueprint_trust.py"


def test_product_paths_no_longer_import_vendor_trust_module():
    deploy_trust_source = DEPLOY_TRUST_PATH.read_text(encoding="utf-8")
    graph_sync_source = GRAPH_SYNC_PATH.read_text(encoding="utf-8")

    assert "from commander_blueprint_trust import check_digest_policy, verify_image_signature" in deploy_trust_source
    assert "from trust import check_digest_policy, verify_image_signature" not in deploy_trust_source

    assert "from commander_blueprint_trust import evaluate_blueprint_trust" in graph_sync_source
    assert "from trust import evaluate_blueprint_trust" not in graph_sync_source


def test_local_blueprint_trust_defines_official_blueprint_truth_locally():
    source = LOCAL_TRUST_PATH.read_text(encoding="utf-8")

    assert "OFFICIAL_BLUEPRINT_IDS = frozenset(" in source
    assert "from .store import OFFICIAL_BLUEPRINT_IDS" not in source
    assert "def evaluate_image_trust(" in source
    assert "def evaluate_blueprint_trust(" in source
    assert "def check_digest_policy(" in source
    assert "def verify_image_signature(" in source
