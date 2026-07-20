from core.output.claim_classifier import classify_claim
from core.output.evidence_contracts import ClaimType


def test_classify_claim_detects_runtime_hardware():
    claim = classify_claim("Wie viel RAM oder VRAM hast du gerade?")
    assert claim.claim_type == ClaimType.RUNTIME_HARDWARE
    assert claim.required_truth_source == "hardware_runtime_tool"


def test_classify_claim_detects_runtime_time():
    claim = classify_claim("Wie viel Uhr ist es gerade?")
    assert claim.claim_type == ClaimType.RUNTIME_TIME
    assert claim.required_truth_source == "time_runtime_tool"


def test_classify_claim_detects_file_content():
    claim = classify_claim("Lies die Datei /trion-home/status.txt.")
    assert claim.claim_type == ClaimType.FILE_CONTENT
    assert claim.required_truth_source == "file_read_tool"


def test_classify_claim_detects_container_runtime():
    claim = classify_claim("Welche Container laufen gerade?")
    assert claim.claim_type == ClaimType.CONTAINER_RUNTIME
    assert claim.required_truth_source == "container_runtime_tool"


def test_classify_claim_detects_skill_inventory():
    claim = classify_claim("Welche Skills und Tools hast du installiert?")
    assert claim.claim_type == ClaimType.SKILL_INVENTORY
    assert claim.required_truth_source == "skill_or_tool_inventory"


def test_classify_claim_does_not_treat_generic_tool_usage_as_inventory():
    claim = classify_claim("Nutze bitte das passende Tool für die Aufgabe.")
    assert claim.claim_type == ClaimType.CONCEPTUAL_ANALYSIS


def test_classify_claim_falls_back_to_conceptual_analysis():
    claim = classify_claim("Wie würdest du die Architektur für einen Anti-Halluzinationsguard aufbauen?")
    assert claim.claim_type == ClaimType.CONCEPTUAL_ANALYSIS
    assert claim.required_truth_source == "none"
