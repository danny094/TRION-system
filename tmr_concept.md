# TRION Meaning Representation (TMR): Making AI Understand Intent Consistent

When interacting with AI agents, users express the same request in countless different ways. They might use German, English, a mix of both, or different sentence structures. For example:
* *"Welche Container sind aktiv?"* (German)
* *"What is running in the home space?"* (English)
* *"Was läuft im Home-Space?"* (Mixed)

If an AI system maps these raw text prompts directly to tools, any slight variation in wording can lead to unpredictable behavior, wrong tool selections, or safety bypasses.

TRION solves this using **TMR (TRION Meaning Representation)**.

---

## What is TMR?

TMR is TRION's semantic normalization layer. Inspired by Abstract Meaning Representation (AMR), TMR acts as a translator that converts natural language input into a structured, language-independent representation of **meaning**.

```
Natural Language Input (DE, EN, Mixed)
                 │
                 ▼
    [ TMR (Meaning Representation) ]  <── "What does the user mean?"
                 │
                 ▼
      [ Operation Contract ]          <── "What is the agent allowed to do?"
                 │
                 ▼
        [ Pipeline Execution ]
```

By decoupling the *meaning* of a request from the *execution* of the request, TRION gains two major advantages:
1. **Paraphrase Invariance:** The system behaves identically whether a user asks formally, colloquially, in German, or in English.
2. **Deterministic Safety:** Meaning is analyzed first. Only after the meaning is established does a separate control layer (the Operation Contract) decide if that meaning is safe to execute.

---

## How It Works in Practice

When a user submits a query, TMR extracts the core **Predicate** (the action or state), the **Theme** (the subject), and the **Scope** or **Target** (where or what is affected).

Here is how different phrasings map to the exact same semantic structure:

| User Query | Predicate (Action) | Theme (Subject) | Scope (Where) |
|---|---|---|---|
| *Was laeuft zuhause?* | `runtime_state` | `container` | `home` |
| *Which containers are active?* | `runtime_state` | `container` | *None* |
| *Was laeuft im Home-Space?* | `runtime_state` | `container` | `home` |

If the user adds details—for example, *"Show ports and mounts of trion-home"*—TMR extracts the target (`trion-home`) and the requested details (`ports`, `mounts`) as static concepts.

---

## Key Benefits of TMR

> [!TIP]
> **Language & Phrasing Independence**
> TMR guarantees that your custom tools and pipelines receive the same clean semantic signal regardless of how the user phrased their request.

* **Fewer Hallucinations:** Because the AI planner receives a structured, validated semantic frame instead of raw conversational text, it is far less likely to select the wrong tools.
* **Safer Execution:** The agent cannot be tricked by clever phrasing or prompt injection into running disallowed commands, because the downstream safety layer checks the structured semantic concepts, not the raw user text.
* **Configurability:** Admins can expand TRION's vocabulary by simply updating concept files in the behavior layer without touching Python code.
