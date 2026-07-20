"""
config.models.tool_selector
============================
Konfiguration des Tool-Selectors (Layer 0 — semantisches Vorfiltern).

Der Tool-Selector ist ein eigenständiges Lightweight-Modell (z.B. qwen2.5:1.5b),
das vor dem Thinking-Layer aus allen verfügbaren Tools die relevantesten
Kandidaten herausfiltert, um Prompt-Bloat zu vermeiden.

TOOL_SELECTOR_CANDIDATE_LIMIT         : Max. Anzahl Kandidaten die weitergereicht werden.
TOOL_SELECTOR_MIN_SIMILARITY          : Untere semantische Schwelle (Reject-Floor).
TOOL_SELECTOR_HIGH_SIMILARITY         : Hohe semantische Schwelle (Strong-Match).
TOOL_SELECTOR_LEXICAL_SUPPORT_MIN     : Mindest-Lexical-Support in der Grauzone.
TOOL_SELECTOR_AMBIGUITY_MARGIN        : Mindestabstand zwischen Platz 1 und 2.
TOOL_SELECTOR_STRONG_LEXICAL_BOOST    : Kleiner Lexical-Boost fuer starke Kandidaten.
TOOL_SELECTOR_WEAK_LEXICAL_BOOST      : Etwas groesserer Lexical-Boost in der Grauzone.
TOOL_SELECTOR_LEXICAL_ONLY_MIN        : Mindestscore fuer degraded lexical-only Mode.
TOOL_SELECTOR_LEXICAL_ONLY_KEYWORD_HITS_MIN : Mindestzahl an Keyword-Hits im degraded Mode.
ENABLE_TOOL_SELECTOR                  : Master-Toggle zum Deaktivieren des gesamten Selektors.
"""
import os

from config.infra.adapter import settings


def get_tool_selector_model() -> str:
    return settings.get(
        "TOOL_SELECTOR_MODEL",
        os.getenv("TOOL_SELECTOR_MODEL", "qwen2.5:1.5b-instruct"),
    )


def get_tool_selector_candidate_limit() -> int:
    """
    Max. Kandidaten-Anzahl aus dem semantischen Vorfilter.
    Begrenzt auf 3–25 um Prompt-Bloat zu vermeiden.
    """
    val = int(settings.get(
        "TOOL_SELECTOR_CANDIDATE_LIMIT",
        os.getenv("TOOL_SELECTOR_CANDIDATE_LIMIT", "10"),
    ))
    return max(3, min(25, val))


def get_tool_selector_min_similarity() -> float:
    """
    Minimaler Ähnlichkeits-Score für den semantischen Vorfilter.
    Höhere Werte reduzieren Over-Selection-Rauschen.
    """
    try:
        val = float(settings.get(
            "TOOL_SELECTOR_MIN_SIMILARITY",
            os.getenv("TOOL_SELECTOR_MIN_SIMILARITY", "0.45"),
        ))
    except Exception:
        val = 0.45
    return max(0.0, min(0.95, val))


def get_tool_selector_high_similarity() -> float:
    """
    Hohe semantische Schwelle fuer starke Tool-Kandidaten.
    Kandidaten oberhalb dieses Werts duerfen mit kleinem Lexical-Boost ranken.
    """
    try:
        val = float(settings.get(
            "TOOL_SELECTOR_HIGH_SIMILARITY",
            os.getenv("TOOL_SELECTOR_HIGH_SIMILARITY", "0.80"),
        ))
    except Exception:
        val = 0.80
    return max(0.0, min(0.99, val))


def get_tool_selector_lexical_support_min() -> int:
    """
    Mindest-Lexical-Support fuer semantische Grauzonen-Kandidaten.
    Unterhalb dieser Schwelle wird der Kandidat verworfen.
    """
    try:
        val = int(settings.get(
            "TOOL_SELECTOR_LEXICAL_SUPPORT_MIN",
            os.getenv("TOOL_SELECTOR_LEXICAL_SUPPORT_MIN", "2"),
        ))
    except Exception:
        val = 2
    return max(0, min(20, val))


def get_tool_selector_ambiguity_margin() -> float:
    """
    Mindestabstand zwischen Platz 1 und Platz 2.
    Kleine Margins signalisieren unsichere Matches und fuehren zu "kein Tool".
    """
    try:
        val = float(settings.get(
            "TOOL_SELECTOR_AMBIGUITY_MARGIN",
            os.getenv("TOOL_SELECTOR_AMBIGUITY_MARGIN", "0.08"),
        ))
    except Exception:
        val = 0.08
    return max(0.0, min(0.5, val))


def get_tool_selector_strong_lexical_boost() -> float:
    """
    Kleiner Lexical-Boost fuer starke semantische Treffer.
    Lexical darf starke Kandidaten nur verfeinern, nicht dominieren.
    """
    try:
        val = float(settings.get(
            "TOOL_SELECTOR_STRONG_LEXICAL_BOOST",
            os.getenv("TOOL_SELECTOR_STRONG_LEXICAL_BOOST", "0.20"),
        ))
    except Exception:
        val = 0.20
    return max(0.0, min(1.0, val))


def get_tool_selector_weak_lexical_boost() -> float:
    """
    Lexical-Boost fuer semantische Grauzonen.
    Nur Kandidaten mit ausreichendem Lexical-Support bleiben hier ueberhaupt im Spiel.
    """
    try:
        val = float(settings.get(
            "TOOL_SELECTOR_WEAK_LEXICAL_BOOST",
            os.getenv("TOOL_SELECTOR_WEAK_LEXICAL_BOOST", "0.35"),
        ))
    except Exception:
        val = 0.35
    return max(0.0, min(1.0, val))


def get_tool_selector_lexical_only_min() -> int:
    try:
        val = int(settings.get(
            "TOOL_SELECTOR_LEXICAL_ONLY_MIN",
            os.getenv("TOOL_SELECTOR_LEXICAL_ONLY_MIN", "6"),
        ))
    except Exception:
        val = 6
    return max(0, min(30, val))


def get_tool_selector_lexical_only_keyword_hits_min() -> int:
    try:
        val = int(settings.get(
            "TOOL_SELECTOR_LEXICAL_ONLY_KEYWORD_HITS_MIN",
            os.getenv("TOOL_SELECTOR_LEXICAL_ONLY_KEYWORD_HITS_MIN", "2"),
        ))
    except Exception:
        val = 2
    return max(0, min(10, val))


# Backward-compat — beim Import eingefroren, Getter bevorzugen
TOOL_SELECTOR_MODEL = get_tool_selector_model()
TOOL_SELECTOR_CANDIDATE_LIMIT = get_tool_selector_candidate_limit()
TOOL_SELECTOR_MIN_SIMILARITY = get_tool_selector_min_similarity()
TOOL_SELECTOR_HIGH_SIMILARITY = get_tool_selector_high_similarity()
TOOL_SELECTOR_LEXICAL_SUPPORT_MIN = get_tool_selector_lexical_support_min()
TOOL_SELECTOR_AMBIGUITY_MARGIN = get_tool_selector_ambiguity_margin()
TOOL_SELECTOR_STRONG_LEXICAL_BOOST = get_tool_selector_strong_lexical_boost()
TOOL_SELECTOR_WEAK_LEXICAL_BOOST = get_tool_selector_weak_lexical_boost()
TOOL_SELECTOR_LEXICAL_ONLY_MIN = get_tool_selector_lexical_only_min()
TOOL_SELECTOR_LEXICAL_ONLY_KEYWORD_HITS_MIN = get_tool_selector_lexical_only_keyword_hits_min()
ENABLE_TOOL_SELECTOR = settings.get(
    "ENABLE_TOOL_SELECTOR",
    os.getenv("ENABLE_TOOL_SELECTOR", "true").lower() == "true",
)
