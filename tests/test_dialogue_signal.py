from core.dialogue_signal.classifier import classify_dialogue_signal, is_conversational_dialogue_act


def test_classify_dialogue_signal_marks_reflective_question_as_smalltalk():
    signal = classify_dialogue_signal("Wie ist es für dich, dass wir dir einen Container als Zuhause erstellt haben?")

    assert signal.dialogue_act == "smalltalk"
    assert signal.response_tone == "warm"
    assert is_conversational_dialogue_act(signal) is True


def test_classify_dialogue_signal_marks_feedback_as_feedback():
    signal = classify_dialogue_signal("Das war zu hart formuliert.")

    assert signal.dialogue_act == "feedback"
    assert signal.response_tone == "mirror_user"
    assert is_conversational_dialogue_act(signal) is True


def test_classify_dialogue_signal_keeps_runtime_request_as_request():
    signal = classify_dialogue_signal("Prüfe den Container trion-home und zeige mir nur verifizierte Home-Metadaten.")

    assert signal.dialogue_act == "request"
    assert is_conversational_dialogue_act(signal) is False


def test_classify_dialogue_signal_marks_ack_as_ack():
    signal = classify_dialogue_signal("Passt.")

    assert signal.dialogue_act == "ack"
    assert signal.response_tone == "mirror_user"
    assert is_conversational_dialogue_act(signal) is True


def test_classify_dialogue_signal_marks_analysis_as_analysis():
    signal = classify_dialogue_signal("Analysiere das Problem bitte genauer.")

    assert signal.dialogue_act == "analysis"
    assert signal.response_tone == "neutral"
    assert is_conversational_dialogue_act(signal) is False


def test_classify_dialogue_signal_marks_question_as_question():
    signal = classify_dialogue_signal("Was bedeutet das eigentlich?")

    assert signal.dialogue_act == "question"
    assert is_conversational_dialogue_act(signal) is False


def test_classify_dialogue_signal_defaults_to_request_for_unmatched_text():
    signal = classify_dialogue_signal("Interessant.")

    assert signal.dialogue_act == "request"
    assert signal.response_tone == "neutral"
    assert is_conversational_dialogue_act(signal) is False
