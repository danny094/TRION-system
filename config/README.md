# Config

Zentraler Konfigurations-Layer für TRION.
Alle Einstellungen kommen aus Umgebungsvariablen — kein hardcodierter Wert im Code.

---

## Struktur

```
config/
├── __init__.py        ← Einstiegspunkt, re-exportiert alle Getter
├── models/
│   ├── llm.py         ← Thinking/Control/Output Modelle
│   ├── providers.py   ← Provider-Normalisierung
│   ├── embedding.py   ← Embedding-Modell + Endpunkt-Modus
│   └── tool_selector.py ← Tool-Selector Modell
├── infra/
│   ├── services.py    ← OLLAMA_BASE, MCP_BASE, DB_PATH
│   ├── paths.py       ← WORKSPACE_BASE, LOG_LEVEL
│   ├── cors.py        ← CORS-Konfiguration
│   └── adapter.py     ← Settings-Adapter
├── pipeline/
│   ├── control_layer.py ← Control-Timeouts, Thresholds
│   ├── query_budget.py  ← Query-Budget, Response-Mode
│   ├── domain_router.py ← Domain-Router, Tool-Injection
│   ├── grounding.py     ← Memory-Timeouts, Context-Limits
│   ├── loop_engine.py   ← Task-Loop-Steuerung
│   └── thinking.py      ← Thinking-Analyzer Enable + Timeout
├── output/
│   ├── char_limits.py   ← Hard-Caps, Soft-Targets
│   ├── streaming.py     ← Streaming-Timeouts, Postcheck
│   └── jobs.py          ← Deep-Job/Autonomy-Job Limits
├── autonomy/
│   ├── scheduler.py     ← Cron-Scheduler Konfiguration
│   ├── trion_policy.py  ← TRION Safe-Mode, Approval-Policy
│   └── hardware_guard.py ← CPU/RAM-Limits für Cron
├── context/
│   ├── chunking.py      ← Text-Chunking Konfiguration
│   ├── retrieval.py     ← JIT-Retrieval Limits
│   └── small_model.py   ← Small-Model-Mode
├── features/
│   ├── security.py      ← Security Feature-Flags
│   └── typedstate.py    ← TypedState Feature-Flags
├── digest/
│   ├── policy.py        ← Digest-Policy
│   ├── schedule.py      ← Digest-Schedule
│   └── storage.py       ← Digest-Storage
└── skills/
    ├── registry.py      ← Skill-Registry Konfiguration
    ├── rendering.py     ← Skill-Rendering
    └── secrets.py       ← Skill-Secrets Policy
```

---

## Nutzung

```python
# Direkt aus config importieren (empfohlen)
from config import get_thinking_model, get_output_provider, OLLAMA_BASE

# Oder aus Sub-Package
from config.models.llm import get_thinking_model
from config.infra.services import OLLAMA_BASE
```

---

## Wichtige Getter

```python
# Modelle
get_thinking_model()     → str   # Default: deepseek-r1:8b
get_control_model()      → str   # Default: qwen2.5:7b
get_output_model()       → str   # Default: qwen2.5:14b
get_embedding_model()    → str

# Provider
get_thinking_provider()  → str   # "ollama" | "ollama_cloud" | "openai" | "anthropic" | "openrouter" | "deepseek" | "minimax"
get_control_provider()   → str
get_output_provider()    → str

# Timeouts
get_output_timeout_interactive_s()  → float
get_output_timeout_deep_s()         → float
get_memory_lookup_timeout_s()       → float
get_control_timeout_interactive_s() → float

# Task Loop
get_task_loop_max_steps()              → int
get_task_loop_max_retries_per_step()   → int
get_task_loop_max_replans()            → int

# Thinking
get_thinking_analyzer_enable()         → bool
get_thinking_timeout_s()               → float

# Verifier / Control LLM rollout
get_control_llm_check_enable()         → bool
get_control_llm_check_long_document_enable() → bool
get_control_llm_check_modes()          → list[str]  # off|long_document|task_loop|needs_confirmation|all

# Secrets
get_secret_resolve_miss_ttl_s()          → int
get_secret_resolve_not_found_ttl_s()     → int

# Infra
OLLAMA_BASE   → str   # http://ollama:11434
MCP_BASE      → str
DB_PATH       → str
```

---

## Regeln

- **Nur Umgebungsvariablen** — kein hardcodierter Wert
- **Sinnvolle Defaults** — funktioniert ohne ENV-Var
- **Kein Import aus `core/` oder `utils/`** — config ist die unterste Schicht
- **Alle Getter sind pure** — kein State, kein Side-Effect
