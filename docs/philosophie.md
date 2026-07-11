# Philosophy

Control through architecture. Most AI systems delegate control to the model. TRION delegates control to the architecture.

---

## Decided once. Valid everywhere.

```
routing_frame → operation_contract → all layers
```

The `routing_frame` is built once. The `operation_contract` is set once. No downstream module re-reads the raw text to re-answer the same question.

What the pipeline decided applies — for Orchestrator, Thinking, Task Loop, and Output simultaneously. No module interprets, no module overrides, no module guesses.

This is not an optimisation. It is the definition of control.

---

## Three LLM calls. No more.

```
Classifier: 0  ·  Orchestrator: 0  ·  Task Loop: 0
Thinking: 1    ·  Verifier: 1      ·  Output: 1
───────────────────────────────────────────────────
Total: 3 LLM calls per request
```

More model is not the answer. The architecture defines where the model is allowed to think — and where deterministic code is the better choice.

Tool selection, routing, and execution happen without an LLM call. Not because it's cheaper. Because an LLM makes worse decisions at these points than deterministic code — and because every LLM call is a potential failure point.

---

## No fallback to raw text.

```python
# without operation_contract
eligible_tools = []

# guessing is not a path
```

The layer that derived tool selection from user text wasn't refactored. It was deleted.

If no `operation_contract` exists, tool selection returns empty. No fallback to a heuristic interpretation of the raw text. No "I'll try anyway."

The system waits until a valid contract exists — or returns a clean error.

---

## Errors are called errors.

```
done = required_evidence ⊆ observed_evidence  ·  else: blocked
```

Missing arguments block before execution. Tool success alone does not complete a task. Unknown completion criteria are not treated as satisfied.

The system says "I don't know" instead of guessing. "Blocked" is a system state, not a failure in the negative sense — it is the correct response to incomplete evidence.

The alternative — guessing, hallucinating, answering with gaps — is not an answer. It is a malfunction that looks like one.

---

← [Back to overview](../README.md)
