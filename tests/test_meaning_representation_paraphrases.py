"""P11 SP1 — TMR-Paraphrasen-Beweise (Doc 55 "Geplante Beweise"):

DE/EN-Paraphrasen, Negation, Modalitaet und Entitaetserhalt; ausserdem die
beiden Property-Beweise aus dem P11-Plan:
  - gleiche Bedeutung -> gleiche TMR
  - verschiedene Bedeutung -> getrennte TMR

Beispieltexte sind woertlich aus Doc 55 (Beispieltabelle) und Doc 56
(Beispieltabelle "Zeig Ports und Mounts von trion-home" / "Starte
trion-home") entnommen, nicht erfunden.

Rot-Zustand vor Implementierung: `build_meaning_representation` existiert
noch nicht in core.routing_frame.meaning -> ImportError.
"""

from core.routing_frame.meaning import build_meaning_representation


def test_doc55_paraphrases_same_meaning_same_predicate_theme_temporal():
    # Doc 55 Beispieltabelle: alle drei -> runtime_state/container/current.
    a = build_meaning_representation("Was laeuft zuhause?")
    b = build_meaning_representation("Welche Container sind aktiv?")
    c = build_meaning_representation("Was laeuft im Home-Space?")

    for tmr in (a, b, c):
        assert tmr.predicate == "runtime_state"
        assert tmr.theme == "container"
        assert tmr.temporal == "current"

    # Doc 55: nur Zeile 1 und 3 tragen scope_candidates=[home]; Zeile 2 leer.
    assert a.scope_candidates == ("home",)
    assert c.scope_candidates == ("home",)
    assert b.scope_candidates == ()


def test_doc55_paraphrases_no_explicit_detail_tokens_stay_empty():
    tmr = build_meaning_representation("Was laeuft zuhause?")
    assert tmr.requested_details == ()


def test_doc56_target_and_details_from_explicit_tokens_only():
    # Doc 56 Beispieltabelle: "Zeig Ports und Mounts von trion-home".
    tmr = build_meaning_representation("Zeig Ports und Mounts von trion-home")
    assert tmr.target_candidates == ("trion-home",)
    assert set(tmr.requested_details) == {"ports", "mounts"}


def test_doc56_lifecycle_action_sets_mutation_candidate():
    # Doc 56 Beispieltabelle: "Starte trion-home".
    tmr = build_meaning_representation("Starte trion-home")
    assert tmr.predicate == "lifecycle_action"
    assert tmr.target_candidates == ("trion-home",)
    assert tmr.mutation_candidate is True


def test_negation_sets_polarity_negative():
    tmr = build_meaning_representation("Die Container laufen nicht mehr")
    assert tmr.polarity == "negative"


def test_modality_can_and_mutation_candidate_on_action_question():
    tmr = build_meaning_representation("Kannst du den Container neustarten?")
    assert tmr.modality == "can"
    assert tmr.predicate == "lifecycle_action"
    assert tmr.mutation_candidate is True


def test_en_paraphrase_preserves_entities_across_language():
    tmr = build_meaning_representation("What is running at home?")
    assert tmr.predicate == "runtime_state"
    assert tmr.theme == "container"
    assert tmr.scope_candidates == ("home",)


def test_property_same_meaning_yields_equal_tmr():
    first = build_meaning_representation("Was laeuft zuhause?")
    second = build_meaning_representation("Was laeuft zuhause?")
    assert first == second


def test_property_different_meaning_yields_different_tmr():
    runtime_query = build_meaning_representation("Was laeuft zuhause?")
    lifecycle_action = build_meaning_representation("Starte trion-home")
    assert runtime_query.predicate != lifecycle_action.predicate
    assert runtime_query != lifecycle_action


def test_no_unmatched_text_is_invented_into_target_candidates():
    # "kein Erraten": ein Text ohne bekannten Alias darf keinen Target liefern.
    tmr = build_meaning_representation("Was laeuft zuhause?")
    assert tmr.target_candidates == ()
