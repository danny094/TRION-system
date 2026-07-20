# Output

Generiert die finale Antwort an den User.
Wird nach Control-Verifier aufgerufen — entweder direkt (einfache Anfragen) oder nach dem Task Loop (multi-step).

**Einzige Aufgabe:** Aus dem verifizierten Plan und dem Kontext eine Antwort streamen.

---

## Status

- ✅ `contracts.py` implementiert
- ✅ `output.py` Verdrahtung implementiert
- ✅ `stream.py` LLM-Call mit System-Prompt + einfachem Postcheck implementiert
- ✅ `messages.py` Message-Array-Aufbau implementiert
- ✅ `prompts.py` System-Prompt aus Persona + Plan + Context implementiert
- ✅ `prompts.py` laedt jetzt auch aktive Contract-Guards fuer Grounding,
  Analyse und fehlendes Memory situationsabhängig zur Laufzeit
- ✅ chunk-weises Streaming via optionalem `chunk_sink`-Callback aktiv (siehe [[05-adapters#Chat-Flow-Admin-API|Adapters]])

---

## Modulstruktur

```
core/output/
├── output.py     ← Einstiegspunkt
├── contracts.py  ← Datenstrukturen
├── evidence_contracts.py ← Claim-/Evidence-/Guard-Basisverträge
├── claim_classifier.py ← erste Claim-Typ-Erkennung für strikte Evidence-Policy
├── evidence_guard.py ← kleiner Guard für grounded Einzeltool-Antworten
├── grounding_state.py ← flüchtiger conversation-lokaler Grounding-State mit TTL
├── stream.py     ← LLM-Call + Streaming + Postcheck
├── messages.py   ← Message-Array-Aufbau
└── prompts.py    ← System-Prompt-Builder
```

---

## Dateien

### `output.py`
Einstiegspunkt. Ruft `messages.py` und `stream.py` auf und gibt das `OutputResult` zurück. Enthält nur dünne Verdrahtung plus Hook für den kleinen Evidence-Guard.
**Max 80 Zeilen.**

### `evidence_guard.py`
Kleiner Guard für grounded Einzeltool-Antworten.
Zusätzlich darf er bei Artefakten ohne verifizierte Evidence auf einen engen
`Unbekannt`-Fallback herunterstufen.
Seit der ersten Strict-Evidence-Stufe unterscheidet er zusätzlich grob zwischen
Claim-Typen wie Hardware, Dateiinhalt, Container-Runtime, Skill-Inventar und
konzeptueller Analyse.
Keine Tool-Aufrufe, keine Approval-Logik, kein eigener Runtime-State.
Wichtig: Im regulaeren Chat-Flow gibt es keinen direkten Grounded-Bypass mehr.
Ob die Anfrage fachlich abgeschlossen ist, entscheidet nicht Output, sondern
Thinking/Task Loop.

### `evidence_contracts.py`
Kleine typisierte Basis für die Strict-Evidence-Policy:

- `ClaimType`
- `GuardDecision`
- `EvidenceClaim`
- `EvidenceBundle`

Nur stdlib und Datamodelle, keine Runtime-Logik.

### `claim_classifier.py`
Kleiner deterministischer Classifier für die ersten Claim-Typen.
Noch kein Tool-Routing und kein Ersatz für `core/classifier/`, sondern
eine enge Output-/Evidence-Hilfsschicht.

### `grounding_state.py`
Kleiner flüchtiger Runtime-State für grounded Tool-Evidenz pro Conversation.
Nur TTL-begrenzte Evidence-Snapshots, kein Long-Term-Memory, keine Adapter-Logik,
keine Persistenzpflicht.

### `contracts.py`
Alle Datenstrukturen: `OutputRequest`, `OutputResult`.
Importiert **nichts** aus dem eigenen Modul — nur stdlib.
**Max 80 Zeilen.**

```python
@dataclass
class OutputRequest:
    user_text: str
    thinking_plan: ThinkingPlan       # Von Thinking / Task Loop
    context: Dict[str, Any]           # Memory, Tool-Ergebnisse, Chat-History
    stream: bool = True

@dataclass
class OutputResult:
    content: str                      # Finale Antwort
    truncated: bool                   # Durch char_cap abgeschnitten
    postcheck_applied: bool           # Postcheck-Fix wurde angewendet
```

### `stream.py`
Einziger LLM-Call im gesamten Output-Modul.
Bei `OutputRequest.stream=True` und übergebenem `chunk_sink` nutzt es
`stream_chat()` aus `core/llm` und reicht jeden Token-Chunk direkt an den Sink
weiter; `OutputResult.content` wird dabei am Ende aus den Chunks
zusammengesetzt. Ohne Sink (oder bei `stream=False`) fällt es auf den
non-streaming `complete_chat()` Pfad zurück.
Postcheck (Hollow-Prefix-Stripping) greift einmalig am ersten Chunk vor dem
Sink-Aufruf — der Stream bleibt sauber und kein nachträgliches Korrigieren
nötig.
**Max 200 Zeilen.**

### `messages.py`
Baut das Message-Array für den LLM-Call: `[system, ...history, user]`.
Ruft `prompts.py` für den System-Prompt auf.
Chat-History: max. 10 vorherige Turns.
Keine LLM-Calls, keine Business-Logik.
**Max 100 Zeilen.**

### `prompts.py`
Baut den System-Prompt sektionsweise aus `intelligence_modules`.
Kein hardcodierter Prompt-Text im Code — alles aus den Prompt-Templates.

Sektionen in Reihenfolge:
1. Persona-Basis
2. aktive Contract-Guards fuer Grounding / Analyse / Memory-Halluzination
3. Plan-Hinweise
4. Memory / Tool-Ergebnisse
5. Antwort-Budget, Stil und Ton ueber die geladenen Prompt-Templates

**Max 150 Zeilen.**

---

## Regeln

- **Max 200 Zeilen pro Datei** — wird eine Datei größer, wird sie aufgeteilt
- **Nur ein LLM-Call im gesamten Modul** — in `stream.py`
- **Kein 6-Datei Grounding-System** — einfacher Postcheck in `stream.py`
- **Kein plan_runtime_bridge** — kein verstecktes Runtime-State-Modul
- **Kein Contract-Handling für Container/Skills** — gehört nicht in Output
- **Kein hardcodierter Prompt-Text** — alles aus `intelligence_modules`
- **`contracts.py` ist das Fundament** — wird zuerst geschrieben, danach nichts mehr daran ändern ohne Review

---

## Entscheidungsfluss

```
OutputRequest eingehend
        ↓
[ messages.py ]   ← baut system + history + user
        ↓
[ stream.py ]     ← LLM-Call, aktuell non-streaming
        ↓
[ postcheck ]     ← einfache Halluzinationsprüfung am Ende
        ↓
OutputResult      → WebUI streamt an User
```

---

## Output

```python
# Normaler Stream
OutputResult(content="...", truncated=False, postcheck_applied=False)

# Antwort wurde abgeschnitten
OutputResult(content="...", truncated=True, postcheck_applied=False)

# Postcheck hat korrigiert
OutputResult(content="...", truncated=False, postcheck_applied=True)
```

---

## Abhängigkeiten

```
output.py
  ├── messages.py
  │     ├── contracts.py
  │     └── prompts.py
  └── stream.py
        ├── contracts.py
        └── core/llm_provider_client.py

intelligence_modules (nur lesend):
  ├── prompts/layers/output*
  ├── cim_skill_rag/output_standards.csv
  └── cim_skill_rag/error_handling_patterns.csv
```

---

## Was Output NICHT macht

- Kein Tool-Routing
- Kein Grounding mit 6 Dateien
- Keine Container- oder Skill-Catalog-Kontrakte
- Kein plan_runtime_bridge oder verstecktes Runtime-State
- Keine Re-Planning-Logik
- Keine Entscheidung über execution_mode oder turn_mode
