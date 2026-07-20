# Control-Classifier

Erster Schritt in der TRION-Pipeline. Klassifiziert den User-Input bevor irgendein LLM aufgerufen wird.

**Einzige Aufgabe:** Input analysieren und entscheiden was als nächstes passiert.

---

## Status

- ✅ `contracts.py` implementiert
- ✅ `classifier.py` deterministische Routing-Entscheidung gegen `cim_policy.csv`
- ✅ `patterns.py` lädt und matched Policy-Patterns (mtime-basierter Hot-Reload)
- ✅ Long-Document-Signal (`is_long_document`, `estimated_input_tokens`) vorhanden
- ⏳ `embedding.py`, `loader.py` folgen — semantische Klassifikation noch offen

---

## Modulstruktur

```
core/classifier/
├── classifier.py     ← Mapping Pattern-Match → ClassifierResult
├── patterns.py       ← CSV-Loader + Regex-Matching gegen cim_policy.csv
└── contracts.py      ← Datenstrukturen
```

---

## Dateien

### `classifier.py`
Einstiegspunkt des Moduls. Holt einen Pattern-Match aus `patterns.py` und mappt
ihn auf `Category`, `SafetyLevel`, `Route`, `needs_orchestrator`. Ohne Match
bleibt der Default `information / safe / direct_to_thinking` bestehen.

Zusätzlich berechnet `classifier.py`:
- `estimated_input_tokens`
- `is_long_document`

**Max 80 Zeilen.**

### `patterns.py`
Lädt `intelligence_modules/cim_policy/cim_policy.csv`, kompiliert die Regexes
und liefert das passende `PatternMatch`. Sortiert nach `priority`
(critical > high > normal > low). Cache wird bei mtime-Änderung der CSV
invalidiert (Hot-Reload).
**Max 200 Zeilen.**

### `contracts.py`
Alle Datenstrukturen des Classifiers: `ClassifierResult`, `Category`, `SafetyLevel`, `Route`.
Importiert **nichts** aus dem eigenen Modul — nur Python stdlib.
Wird von allen anderen Dateien importiert, importiert selbst niemanden.
**Max 80 Zeilen.**

```python
Category:     smalltalk | risk | tool | planning | information | unknown
SafetyLevel:  safe | warning | block
Route:        direct_to_thinking | needs_orchestrator | block
```

### Geplante Ausbaustufen
`embedding.py` und `loader.py` bleiben Zielbild für einen späteren semantischen
Classifier (Embedding-basierte Intent-Erkennung). Sie existieren noch nicht im
Runtime-Code. `patterns.py` ist seit dem Schritt zur produktiven Routing-Logik
verdrahtet.

---

## Regeln

- **Max 200 Zeilen pro Datei** — wird eine Datei größer, wird sie aufgeteilt
- **Jede Datei hat genau eine Aufgabe** — keine Mischung von Laden, Matching und Verdrahtung
- **Kein hardcodierter Text im Code** — alle Regeln kommen aus `intelligence_modules`
- **Keine Execution-Logik** — der Classifier klassifiziert nur, er führt nichts aus
- **Keine LLM-Calls** — nur 4B Modell für Embeddings, kein vollwertiges LLM
- **`contracts.py` ist das Fundament** — wird zuerst geschrieben, danach nichts mehr daran ändern ohne Review

---

## Output

```python
@dataclass
class ClassifierResult:
    category: Category        # Erkannte Kategorie des Inputs
    safety_level: SafetyLevel # Sicherheitsstufe
    needs_orchestrator: bool  # True = Orchestrator wird benötigt
    confidence: float         # 0.0 - 1.0
    route: Route              # Was als nächstes passiert
    matched_pattern: str      # Welches Pattern hat gematcht
    reason: str               # Warum diese Entscheidung
    is_long_document: bool    # True wenn der Input als Dokument geroutet werden soll
    estimated_input_tokens: int # Grobe Token-Schaetzung fuer Routing
```

---

## Abhängigkeiten

```
classifier.py
  ├── contracts.py
  └── patterns.py
        └── (lädt cim_policy.csv direkt)

intelligence_modules (nur lesend, aktuell verdrahtet):
  └── cim_policy/cim_policy.csv

intelligence_modules (Zielbild für embedding.py / loader.py):
  ├── cim_skill_rag/capability_intent_map_v2.csv
  ├── cim_skill_rag/capability_feature_weights_v2.csv
  ├── cim_skill_rag/execution_mode_signals_v2.csv
  └── cim_skill_rag/intent_category_map.csv
```

---

## Routing-Entscheidung

| Kategorie | Safety | Route |
|-----------|--------|-------|
| smalltalk | safe | direct_to_thinking |
| information | safe | direct_to_thinking |
| planning | safe | needs_orchestrator |
| tool | safe | needs_orchestrator |
| risk | warning | direct_to_thinking + Hinweis |
| risk | block | block |

Hinweis zum aktuellen Stand:
- Die Tabelle wird durch `cim_policy.csv` umgesetzt (siehe `patterns.py`).
- Bei keinem Pattern-Match bleibt der Default `information / safe / direct_to_thinking`.
- `risk` mit `safety_level=critical` wird als `Route.BLOCK` zurückgegeben (kein Output-Pfad).
