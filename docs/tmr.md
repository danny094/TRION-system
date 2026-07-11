# TMR System

TRION Meaning Representation. Meaning is normalised before routing decides. Same intent. Different text. Same route.

```
status: draft — implementation in progress
```

---

## The Problem

Applying routing directly to raw text is unstable. The same request, phrased differently, should take the same route. That does not happen automatically.

```
"Show me the deployment status"
"How's the deployment going right now?"
"deployment status please"
```

Three phrasings. Same intent. Without normalisation: three possible routes.

---

## The Solution

TMR normalises meaning before the `routing_frame` is built.

```
raw_text → TMR → routing_frame
```

The `routing_frame` operates on a normalised meaning representation — not on the raw text. What the user writes is input. What TMR produces from it is the basis for every decision that follows.

---

## Seven axes. One representation.

The `routing_frame` classifies every request along seven dimensions:

```
intent_kind       · type of intent (query · action · creation · ...)
domain            · subject area
evidence_need     · which evidence is required
execution_mode    · simple | complex
confidence        · classification certainty
...               · two further axes
```

TMR delivers the normalised input that makes this classification stable and phrasing-independent.

Without TMR: same axis, different values depending on phrasing.  
With TMR: axis values are phrasing-independent.

---

## Distinction from the Classifier

```
Classifier     →  coarse category · route · safety_level  (pattern-matching)
TMR            →  normalised meaning for the routing_frame
routing_frame  →  7 axes · operation_contract
```

The Classifier is fast and rule-based. TMR is semantic — it is about meaning, not category. Both operate without an LLM call.

---

## Status

The architecture is designed. Implementation is in progress.

```
docs/architecture/  → target design and design decisions
docs/routing/       → routing_frame current state and TMR integration
```

---

← [Back to overview](../README.md)
