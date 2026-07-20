from dataclasses import dataclass


@dataclass(frozen=True)
class DialogueSignal:
    dialogue_act: str
    response_tone: str
    response_length_hint: str
    confidence: float
    classifier_mode: str = "lexical"

