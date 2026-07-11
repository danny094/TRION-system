<div align="center">

<svg width="52" height="46" viewBox="0 0 36 32" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="tri" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#a855f7"/>
      <stop offset="100%" stop-color="#6366f1"/>
    </linearGradient>
  </defs>
  <polygon points="18,2 34,30 2,30" fill="none" stroke="url(#tri)" stroke-width="2.5" stroke-linejoin="round"/>
</svg>

# TRION

**Modular AI system with clean layer architecture.**  
Control through architecture — not through the model.

</div>

---

```
Classifier: 0 LLM  ·  Orchestrator: 0 LLM  ·  Task Loop: 0 LLM
Thinking: 1 LLM    ·  Verifier: 1 LLM       ·  Output: 1 LLM
─────────────────────────────────────────────────────────────────
total: 3 LLM-Calls  ·  no fallback to raw text  ·  fail-closed
```

---

## Architecture

TRION is a sequential pipeline with a single bottleneck. The `routing_frame` is built once and read by all downstream layers. No module re-interprets the request. No decision is made twice.

| Layer | Responsibility | LLM |
|---|---|---|
| **Classifier** | Coarse routing, safety level, category | 0 |
| **routing_frame** | Bottleneck — intent, domain, evidence, operation contract | 0 |
| **Orchestrator** | Tool filtering, context collection (complex path only) | 0 |
| **Thinking** | Plans, selects tools, analyses | 1 |
| **Verifier** | Validates plan against GuardDecision + anti_patterns | 1 |
| **Task Loop** | Deterministic execution, evidence gate | 0 |
| **Output** | Streaming, claim validation | 1 |

---

## Core Principles

```
routing_frame → operation_contract → all layers
```
**Decided once. Valid everywhere.** What the pipeline decided applies to all downstream modules simultaneously.

```
without operation_contract → eligible_tools = []
```
**No fallback to raw text.** The layer that derived tool selection from user text wasn't refactored — it was deleted.

```
done = required_evidence ⊆ observed_evidence  ·  else: blocked
```
**Errors are called errors.** Missing evidence blocks before execution. Tool success alone does not complete a task.

```
Classifier: 0  ·  Orchestrator: 0  ·  Task Loop: 0  ·  Thinking: 1  ·  Verifier: 1  ·  Output: 1
```
**Three LLM calls. No more.** Tool selection, routing, and execution happen without a model.

---

## Documentation

| Document | Content |
|---|---|
| [The Pipeline](./docs/pipeline.md) | Full architecture, both paths, all layers |
| [System Map](./docs/systemkarte.md) | Visual overview of the entire architecture |
| [TMR System](./docs/tmr.md) | TRION Meaning Representation — normalisation before routing |
| [Philosophy](./docs/philosophie.md) | Four architectural ground rules |

### Technical Docs

| Folder | Content |
|---|---|
| [`docs/architecture/`](./docs/architecture/) | System, core and PIANO target design |
| [`docs/routing/`](./docs/routing/) | Routing frame, capability manifest, current state |
| [`docs/memory-grounding/`](./docs/memory-grounding/) | Memory, evidence, self-context |
| [`docs/task-loop/`](./docs/task-loop/) | Autonomy, task loop, error behaviour |
| [`docs/governance/`](./docs/governance/) | Design, lifecycle and veto rules |
| [`docs/implementation-plans/`](./docs/implementation-plans/) | Active and completed plans |

---

<div align="center">
<sub>TRION — <code>code decides over truth</code></sub>
</div>
