# Output Layer

Der Output Layer formuliert und streamt die finale Antwort. Er besitzt genau
einen LLM-Call und konsumiert den typisierten P12-Evidence-Handoff aus der
Pipeline.

## Datenfluss

```text
OutputEvidenceHandoff
  -> build_output_stage
  -> OutputRequest(renderable_evidence)
  -> generate_output Evidence-Preflight
  -> build_output_messages
  -> build_output_system_prompt
  -> Provider / Stream
  -> Execution- und Markup-Guard
  -> OutputResult
```

## Module

| Modul | Verantwortung |
|---|---|
| `contracts.py` | `OutputRequest`, `OutputResult`, `RenderableEvidence` |
| `output.py` | duenne Output-Orchestrierung und Guard-Reihenfolge |
| `stream.py` | einziger LLM-/Stream-Pfad und Chunkguard vor `chunk_sink` |
| `messages.py` | Chat-History und expliziter Prompt-Handoff |
| `prompts.py` | duenne Systemprompt-Komposition |
| `public_contract_prompt.py` | einziger Contract-/Typed-Evidence-Promptowner |
| `renderable_evidence.py` | generische Strukturresultat-Projektion |
| `claim_classifier.py` | typisierte Claim-Klassifikation |
| `evidence_requirements.py` | `GuardDecision` aus Claim und Handoff-State |
| `no_evidence_fallback.py` | einziger fail-closed Evidence-Guard-Owner |
| `execution_consistency_guard.py` | positive Execution-Behauptungen pruefen |
| `tool_markup_guard.py` | recovery-freier Batch-Markup-Schutz |
| `persona_runtime.py` | Persona aus Live-Descriptor-Provenance |
| `grounding_state.py` | interner fluechtiger State ohne Public-Autoritaet |
| `grounded_output_selection.py` | gemeinsamer Textnormalisierer |

## Evidence-Vertrag

`OutputRequest.output_evidence` ist ein verpflichtender immutable
`OutputEvidenceHandoff`. `renderable_evidence` ist ein separates immutable Tuple
aus `RenderableEvidence`; es wird ausschliesslich in
`core/pipeline/output_stage.py` erzeugt.

Nicht erlaubt sind:

- `context["renderable_evidence"]`,
- Rohresultat-, Toolname- oder Dict-Rekonstruktion,
- Memory-, TaskLoop-, Grounding-State-, Home- oder Self-Context als
  Public-Evidence,
- Evidence-Entscheidungen im Prompt oder Provideradapter.

## Guard-Reihenfolge

1. `apply_no_evidence_fallback(..., preflight=True)` blockiert im Streaming
   evidenzpflichtige Claims ohne renderbare validierte Evidence vor Provider und
   Sink; im Batchpfad greift derselbe Guard vor der Antwortprojektion.
2. `_stream_output` prueft jeden Chunk vor `chunk_sink` auf Tool-Markup und
   kumulativ auf unbelegte positive Execution-Behauptungen; verdaechtige
   Prefixe bleiben bis zur Entscheidung pending.
3. `apply_execution_consistency_guard` bleibt die einzige Execution-Policy;
   `_stream_output` platziert sie im Stream, `generate_output` nur im Batch.
4. `apply_tool_markup_guard` prueft den finalen Batchtext ohne Recovery.
5. `apply_no_evidence_fallback` bestaetigt den finalen Evidence-Zustand.

Wenn ein finaler Guard den bereits gestreamten Text ersetzt, transportiert die
Admin-API `final_content`; die WebUI ersetzt damit den bisherigen Inhalt.

## Prompt-Grenze

`prompts.py` komponiert Persona, Basisprompt, Contract, Plan, Dialog und den
typisierten Evidence-Block. `public_contract_prompt.py` baut Contractbloecke aus
User-Intent und autoritativem Routing-Frame-Signal; sein Evidence-Pfad
formatiert nur bereits erzeugte `RenderableEvidence`-Werte.

Die entfernten Legacyprojektionen fuer Memory, TaskLoop-Artefakte,
`grounded_tool_results`, Home-Context und Self-Context besitzen keinen Caller.

## Tests

- `tests/test_output_prompt_split_structure.py`
- `tests/test_output_public_contract.py`
- `tests/test_output_typed_evidence_contract.py`
- `tests/test_output_typed_renderers.py`
- `tests/test_output_streaming.py`
- `tests/test_output_late_guard_final_content.py`
- `tests/test_output_execution_consistency_guard.py`
- `tests/test_webui_chat_final_content_contract.py`

## Grenzen

- Kein LLM-Call im TaskLoop.
- Kein Provider-Retry oder Tool-Routing im Output Layer.
- Keine Public-Evidence-Persistenz ueber Resume.
- Kein Markup-Parsing oder Rohresultat-Recovery.
- P12-Lifecycle-PASS und Live-E2E bleiben separate Gates.
