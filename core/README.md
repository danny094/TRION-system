# TRION Core

---

## Aktueller Implementierungsstand

Die Core-Pipeline wird schrittweise aufgebaut. Der erste stabile Schnitt ist erledigt:

| Modul | Status |
|-------|--------|
| `classifier/contracts.py` | ✅ implementiert |
| `classifier/classifier.py` | ✅ deterministisches Pattern-Routing über `cim_policy.csv`, inkl. Long-Document-Signal |
| `classifier/patterns.py` | ✅ CSV-Loader + Regex-Match mit mtime-Hot-Reload |
| `input_processor/contracts.py` | ✅ implementiert |
| `input_processor/detect.py` | ✅ implementiert |
| `input_processor/chunker.py` | ✅ implementiert |
| `input_processor/storage.py` | ✅ implementiert |
| `input_processor/summarizer.py` | ✅ implementiert |
| `input_processor/processor.py` | ✅ implementiert |
| `orchestrator/contracts.py` | ✅ implementiert |
| `orchestrator/orchestrator.py` | ✅ Minimal-Orchestrator implementiert |
| `orchestrator/tools.py` | ✅ Tool-Auflösung ohne MCP-Import implementiert |
| `orchestrator/context.py` | ✅ Kontextquellen per Injection implementiert |
| `thinking/contracts.py` | ✅ implementiert |
| `thinking/thinking.py` | ✅ Minimalpfad implementiert, inkl. Orchestrator-Kontext |
| `thinking/analyzer.py` | ✅ schlanke Verdrahtung LLM vs. Fallback |
| `thinking/fallback.py` | ✅ klassifier-aware deterministischer Pfad ohne LLM |
| `verifier/contracts.py` | ✅ implementiert |
| `verifier/verifier.py` | ✅ Verdrahtet `input_prepare -> safety -> llm_check` |
| `task_loop/contracts.py` | ✅ implementiert |
| `output/contracts.py` | ✅ implementiert |
| `output/output.py` | ✅ Vertical-Slice-Verdrahtung implementiert |
| `output/stream.py` | ✅ Non-streaming LLM-Call implementiert |
| `pipeline/runner.py` | ✅ Staged Pipeline implementiert |
| `pipeline/thinking_stage.py` | ✅ implementiert |
| `pipeline/output_stage.py` | ✅ implementiert |

Der minimale Vertical Slice ist implementiert:
Classifier → Thinking → Verifier → Output.

Zusätzlich vorhanden:
- komplexer Pfad mit Orchestrator-Stufe
- Task-Loop-Start aus der Pipeline
- Long-Document-Guard über `core/input_processor/`
- erster Thinking-Kontextpfad mit reduzierter Orchestrator-Summary
- Thinking- und Output-Stages als eigene Pipeline-Schnitte
- produktiver Verifier-Pfad mit deterministischem Safety-Check und optionalem LLM-Check

---

## Core Pipeline Zielzustand

`core/pipeline/runner.py` ist die Adapter-Grenze der neuen Pipeline.

Input:
- `CoreChatRequest`

Output:
- `CoreChatResponse`

Erster Pfad:

```
CoreChatRequest
    ↓
classifier.classify()
    ↓
thinking.build_plan()
    ↓
verifier.verify_plan()
    ↓
output.generate_output()
    ↓
CoreChatResponse
```

Komplexer Pfad heute:

```
CoreChatRequest
    ↓
pipeline/preprocess.py
    ↓
pipeline/orchestrator_stage.py
    ↓
thinking.build_plan()
    ↓
verifier.verify_plan()
    ↓
pipeline/task_loop_stage.py
    ↓
output.generate_output()
    ↓
CoreChatResponse
```

Noch offen:
- semantische Classifier-Schaerfung (Embedding-Pfad, `embedding.py`/`loader.py`); deterministisches Pattern-Routing gegen `cim_policy.csv` ist verdrahtet
- kontrollierte Aktivierung von `CONTROL_LLM_CHECK_ENABLE`
- spaetere LLM-Schaerfung und feingranulares Retrieval-Filtering fuer den Dokumentpfad
- Ausbau der produktiven Verifier-Regeln

---

## LLM Provider

Provider-aware Client-Helper für alle LLM-Anfragen.
Neue Implementierung: `core/llm/`.
Kompatibilitäts-Fassade: `core/llm_provider_client.py`.

Unterstützte Provider: `ollama`, `ollama_cloud`, `openai`, `anthropic`, `openrouter`, `minimax`.

### Externe API-Endpunkte

| Provider | Endpunkt | Genutzt von |
|----------|----------|-------------|
| Ollama (lokal) | `POST /api/generate` | `complete_prompt`, `stream_prompt` |
| Ollama (lokal) | `POST /api/chat` | `complete_chat`, `stream_chat` |
| Ollama Cloud | `POST /api/chat` | alle Funktionen |
| OpenAI | `POST /v1/chat/completions` | alle Funktionen |
| Anthropic | `POST /v1/messages` | alle Funktionen |
| OpenRouter | `POST /api/v1/chat/completions` | alle Funktionen |
| MiniMax | `POST /v1/chat/completions` | alle Funktionen |
| Provider Key Store (intern) | Admin-API / SQLite | API-Key-Auflösung |

### Öffentliche Funktionen

| Funktion | Rückgabe | Beschreibung |
|----------|----------|--------------|
| `complete_prompt(...)` | `str` | Einmaliger Prompt, kein Streaming |
| `stream_prompt(...)` | `AsyncGenerator[str]` | Streaming-Prompt |
| `complete_chat(...)` | `dict` (content + tool_calls) | Chat mit Message-History |
| `stream_chat_events(...)` | `AsyncGenerator[dict]` | Streaming mit `type` + `chunk` (inkl. Thinking) |
| `stream_chat(...)` | `AsyncGenerator[str]` | Convenience-Wrapper um `stream_chat_events` |
| `get_rate_limit_snapshot()` | `dict` | Rate-Limit-Status aller Provider |

### Modulstruktur

| Datei | Aufgabe |
|-------|---------|
| `core/llm/provider_registry.py` | Zentrale Provider-Metadaten, Rollenaufloesung, Base-URLs, Preset-Metadaten |
| `core/llm/providers/` | Laufzeitmodule pro Provider bzw. Providerpfad |
| `core/llm/secrets.py` | API-Key-Auflösung aus dem verschluesselten Provider-Key-Store und internem Resolve-Pfad |
| `core/llm/rate_limits.py` | Rate-Limit-Snapshot |
| `core/llm/messages.py` | Message-Normalisierung |
| `core/llm/ollama.py` | Kompatibilitaetsfassade fuer Ollama-Importpfade |
| `core/llm/openai.py` | Kompatibilitaetsfassade fuer OpenAI-Importpfade |
| `core/llm/anthropic.py` | Kompatibilitaetsfassade fuer Anthropic-Importpfade |
| `core/llm/chat.py` | `complete_chat()` Dispatch |
| `core/llm/streaming.py` | Chat-Streaming Dispatch |
| `core/llm/prompts.py` | Prompt-Kompatibilitätsfunktionen |

Hinweis zum Chat-Fehlerpfad:

- `adapters/admin-api/chat_stream.py` uebersetzt Providerfehler in nutzerlesbare NDJSON-Events
- strukturierte Felder: `error_code`, `error_provider`, `error_status`
- typische Faelle: `missing_api_key`, `missing_endpoint`, `401`, `403`, `404`, `429`, Timeout, Connect-Error

Hinweis zum Zielbild:

- Provider-Keys kommen aus dem verschluesselten Provider-Key-Store; ENV-Keys sind fuer LLM-Provider nicht mehr Teil des aktiven Pfads
- langfristig sollen Provider-Secrets aus der WebUI heraus gesetzt und
  verschluesselt im Backend gespeichert werden
- `core/llm/secrets.py` bleibt dabei die einzige interne Aufloesungsschicht
- Secret-Werte duerfen nie an die WebUI zurueckgegeben werden
