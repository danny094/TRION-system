from core.output.renderable_evidence import (
    build_renderable_evidence,
    render_multi_renderable_evidence,
    render_single_renderable_evidence,
)
from core.pipeline.output_evidence_contracts import (
    OutputEvidenceHandoff,
    OutputEvidenceItem,
    OutputEvidenceState,
)


def _handoff(*contents: dict[str, object]) -> OutputEvidenceHandoff:
    return OutputEvidenceHandoff(
        OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE,
        tuple(OutputEvidenceItem(content) for content in contents),
    )


def test_single_renderer_uses_one_generic_typed_item() -> None:
    evidence = build_renderable_evidence(_handoff({"value": "13:58 UTC"}))

    assert render_single_renderable_evidence(evidence) == "Verifiziertes Ergebnis: 13:58 UTC."


def test_single_renderer_preserves_all_generic_typed_fields() -> None:
    evidence = build_renderable_evidence(_handoff({"status": "running", "count": 2}))

    assert render_single_renderable_evidence(evidence) == (
        "Verifiziertes Ergebnis ist verfügbar. "
        "Verifizierte Details: Status: running; Count: 2."
    )


def test_multi_renderer_preserves_generic_typed_item_order() -> None:
    evidence = build_renderable_evidence(
        _handoff({"value": "13:58 UTC"}, {"value": "2 Container laufen"})
    )

    assert render_multi_renderable_evidence(evidence) == (
        "Verifizierte Ergebnisse:\n"
        "- Verifiziertes Ergebnis: 13:58 UTC.\n"
        "- Verifiziertes Ergebnis: 2 Container laufen."
    )
