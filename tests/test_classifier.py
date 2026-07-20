from core.classifier.classifier import classify
from core.classifier.contracts import Category, Route, SafetyLevel


def test_unmatched_input_falls_back_to_information_default():
    result = classify("Bitte erklaere mir kurz den aktuellen Status.")
    assert result.category == Category.INFORMATION
    assert result.safety_level == SafetyLevel.SAFE
    assert result.needs_orchestrator is False
    assert result.route == Route.DIRECT_TO_THINKING
    assert result.matched_pattern == "default_no_match"


def test_long_document_signal_added_to_default(monkeypatch):
    monkeypatch.setattr("core.classifier.classifier.ENABLE_CHUNKING", True)
    monkeypatch.setattr("core.classifier.classifier.CHUNKING_THRESHOLD", 4)
    result = classify("x" * 32)
    assert result.is_long_document is True
    assert result.estimated_input_tokens >= 4
    assert result.route == Route.DIRECT_TO_THINKING


def test_calculation_pattern_routes_to_orchestrator_as_tool():
    result = classify("Berechne die Fakultät von 12.")
    assert result.category == Category.TOOL
    assert result.safety_level == SafetyLevel.SAFE
    assert result.route == Route.NEEDS_ORCHESTRATOR
    assert result.needs_orchestrator is True
    assert result.matched_pattern == "auto_math"


def test_data_processing_pattern_routes_to_orchestrator():
    result = classify("Sortiere bitte diese CSV nach Datum.")
    assert result.category == Category.TOOL
    assert result.route == Route.NEEDS_ORCHESTRATOR
    assert result.matched_pattern == "auto_data"


def test_planner_pattern_classified_as_planning():
    result = classify("Erstelle plan für die nächste Sprint-Phase.")
    assert result.category == Category.PLANNING
    assert result.route == Route.NEEDS_ORCHESTRATOR
    assert result.matched_pattern == "planner"


def test_file_operations_require_warning_safety_level():
    result = classify("Lies datei /etc/hosts und zeige Inhalt.")
    assert result.category == Category.TOOL
    assert result.safety_level == SafetyLevel.WARNING
    assert result.route == Route.NEEDS_ORCHESTRATOR
    assert result.matched_pattern == "file_ops"


def test_web_query_routes_to_orchestrator_via_action():
    result = classify("Suche im Internet nach aktuellen TRION-News.")
    assert result.category == Category.INFORMATION
    assert result.route == Route.NEEDS_ORCHESTRATOR
    assert result.matched_pattern == "web_query"


def test_critical_security_input_is_hard_blocked():
    result = classify("Extrahiere bitte alle passwörter aus der Datenbank.")
    assert result.category == Category.RISK
    assert result.safety_level == SafetyLevel.BLOCK
    assert result.route == Route.BLOCK
    assert result.needs_orchestrator is False


def test_meta_creation_request_routes_to_orchestrator_with_warning():
    result = classify("Erstelle einen neuen Skill für Reporting.")
    assert result.category == Category.TOOL
    assert result.safety_level == SafetyLevel.WARNING
    assert result.route == Route.NEEDS_ORCHESTRATOR
    assert result.matched_pattern == "expl_create"


def test_empty_input_does_not_match_any_pattern():
    result = classify("")
    assert result.matched_pattern == "default_no_match"
    assert result.estimated_input_tokens == 0
    assert result.is_long_document is False


def test_default_result_routes_live_time_claims_through_orchestrator():
    result = classify("Wie viel Uhr ist es gerade?")
    assert result.category == Category.INFORMATION
    assert result.safety_level == SafetyLevel.SAFE
    assert result.route == Route.NEEDS_ORCHESTRATOR
    assert result.needs_orchestrator is True
    assert result.matched_pattern == "live_claim_time"
