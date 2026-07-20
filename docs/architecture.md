# Architecture

TRION is a pipeline of small, single-purpose modules. Each module does **one**
job and knows only its direct neighbors. A request flows through a fixed set of
stages, most of them deterministic — only a few steps ever call an LLM.

The goal is an agent you can reason about: behavior lives in transparent
configuration, not scattered across the codebase, and the path from input to
answer is explicit and auditable.

> The rule-driven foundation behind this design is the **PIANO** pattern —
> see [PIANO — the cognitive engine](../piano_concept.md).

---

## Design principle: rules out of code

No core module carries its own behavioral rules. Routing policies, prompt
templates, tool mappings, and safety rules live in a dedicated, externalized
layer (`intelligence_modules/`). The Python code defines *how* to execute a
task; the configuration defines *what* behavior is allowed.

All classification and safety signals are collected into a single structured
frame — the `routing_frame` — before any downstream module acts. Downstream
modules read from that frame instead of making independent, ad-hoc decisions on
the raw input. This is what keeps safety filters and routing choices consistent
across the whole pipeline.

---

## The pipeline: six modules

### 1. Control-Classifier
Classifies the input **before** any LLM is called. It matches the request
deterministically against pattern rules (`intelligence_modules/`) and returns a
structured result:

- `category` — smalltalk / information / tool / planning / risk
- `route` — `direct_to_thinking` or `needs_orchestrator`
- `safety_level` — safe / warning / block

It also estimates input size and flags long documents. No LLM call.

### 2. Orchestrator
Builds the context and tool path for complex requests. It gathers which tools
are available, which ones fit the request, and what context is needed (memory,
workspace status, active containers), then hands a bounded package to Thinking.
Tool selection is filtered through explicit allow/block lists before Thinking
ever sees the list.

### 3. Thinking
Analyzes the request and produces a structured plan of steps. Thinking is also
the planner — there is no separate planner service. It returns a `ThinkingPlan`
with the steps, a `needs_task_loop` flag, and a risk level. When a later step
fails, a replanner hook can produce a revised plan that continues in the same
loop.

### 4. Control-Verifier
Checks the plan once. A deterministic safety pass runs first; on a hard block it
stops immediately without ever calling an LLM. An optional single LLM check can
be enabled for higher-risk paths. The verdict is one of:

- `APPROVED` → continue
- `REJECTED + hint` → back to Thinking
- `HARD_BLOCK` → stop

### 5. Task Loop
Executes multi-step plans — only when `needs_task_loop` is set. The loop itself
makes **no LLM call**: it runs the tool executor and a deterministic reflect
step. On failure it hands back to the replanner. Step budgets (max steps,
retries, replans) come from configuration, not hard-coded values.

### 6. Output
Generates and streams the final answer. One LLM call, one lightweight
post-check — the answer is grounded against verified results, and when TRION
lacks grounded facts it says so instead of guessing.

---

## The two paths

A deterministic classifier decides which path a request takes.

**Simple path** — smalltalk, direct questions, information requests:

```
Input → Classifier → Thinking → Verifier → Output → User
```

**Complex path** — deploying a container, running a capability, multi-step work:

```
Input → Classifier → Orchestrator → Thinking → Verifier → Task Loop → Output → User
                                                              ↕
                                                        Tool Executor → MCP Hub
```

The classifier only switches to the complex path when a rule matches (tool,
planning, web, or capability actions). Otherwise the request stays on the short
path. The whole route uses just three LLM steps — Thinking, the optional
Verifier check, and Output.

---

## Reflect in the task loop

After each step, the task loop decides what happens next — deterministically,
with no LLM:

```
Step finished
      ↓
Task Loop checks itself (no LLM):
    Result OK + next step   → continue
    All steps done          → Output
    Error / unexpected      → Thinking (replanner)
    Risk gate               → wait for user
```

---

## Supporting layers

### Config
All settings come from environment variables — there are no hard-coded values in
the rest of the code. Modules read configuration through a single `config`
interface, so models, providers, and budgets can be changed without touching
source.

### Memory
Memory is its own **isolated MCP server** built on SQLite plus embeddings. It is
called through the MCP hub, never imported directly. It offers short/mid/long
term layers, semantic search, a knowledge graph, and structured facts.

### Tools
The tool executor sits between the task loop and the MCP hub. It always returns
a structured `ToolResult` and never throws — success or failure is data, not an
exception. A bridge adapter keeps `core/` from importing the tool layer
directly, preserving the one-way dependency direction.

### LLM provider layer
A provider-aware client handles every LLM call behind one interface. Each role —
`CONTROL`, `THINKING`, `OUTPUT` — can point at a different model and provider.

**Supported providers:** OpenAI · Anthropic · OpenRouter · MiniMax · Ollama
(local & cloud).

API keys are never hard-coded. The target architecture stores them encrypted in
the backend and resolves them internally at the LLM layer; the UI only ever sees
status (`set`, `empty`, `test failed`), never plaintext.

---

## Where to go next

- [PIANO — the cognitive engine](../piano_concept.md) — the rule-driven pattern behind the pipeline
- [Operation Contract concept](../operation_contract_concept.md) — how capabilities declare what they do
- [TRION Meaning Representation (TMR)](../tmr_concept.md) — the structured meaning layer
