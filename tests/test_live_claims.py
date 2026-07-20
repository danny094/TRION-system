from core.classifier.live_claims import LiveClaimKind, detect_live_claim_kind


def test_detect_live_claim_kind_for_time_queries():
    assert detect_live_claim_kind("Wie viel Uhr ist es gerade?") == LiveClaimKind.TIME


def test_detect_live_claim_kind_for_non_live_queries():
    assert detect_live_claim_kind("Erkläre mir kurz, wie Embeddings funktionieren.") == LiveClaimKind.NONE


def test_detect_live_claim_kind_ignores_meta_pipeline_discussion():
    text = "Die Pipeline zeigt selected_tools und semantic_score fuer einen container runtime Fall."
    assert detect_live_claim_kind(text) == LiveClaimKind.NONE


def test_detect_live_claim_kind_for_file_queries():
    assert detect_live_claim_kind("Zeige mir den Inhalt der Datei.") == LiveClaimKind.FILE_CONTENT


def test_detect_live_claim_kind_for_hardware_queries():
    assert detect_live_claim_kind("Wie viel RAM ist noch frei?") == LiveClaimKind.HARDWARE


def test_detect_live_claim_kind_for_container_queries():
    assert detect_live_claim_kind("Welche Container laufen gerade?") == LiveClaimKind.CONTAINER_RUNTIME


def test_detect_live_claim_kind_for_skill_queries():
    assert detect_live_claim_kind("Welche Skills sind installiert?") == LiveClaimKind.SKILL_INVENTORY
