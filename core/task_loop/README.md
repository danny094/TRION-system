# Task Loop

Führt einen von Thinking erstellten Multi-Step-Plan aus.
Wird nach Control-Verifier aktiviert wenn `ThinkingPlan.needs_task_loop = True`.

**Einzige Aufgabe:** Schritte sequenziell ausführen, Ergebnisse sammeln, bei Fehlern Thinking aufrufen.

---

## Status

- ✅ `contracts.py` implementiert
- ✅ `reflection.py` minimal implementiert und getestet
- ✅ `executor.py` minimal implementiert und getestet
- ✅ `task_loop.py` implementiert
- ✅ `runner.py` implementiert
- ✅ `continue_task_loop()` erhält `objective` und vorhandene `artifacts`
- ✅ Re-Planning-Hook zu `core/thinking/replanner.py` angeschlossen
- 🔶 Pipeline-Integration vorhanden: `core/pipeline/runner.py` reicht Task-Loop-Kontext an Output weiter

---

## Modulstruktur

```
core/task_loop/
├── task_loop.py      ← Einstiegspunkt
├── contracts.py      ← Datenstrukturen + State Machine
├── runner.py         ← Vorwärtslauf
├── presentation.py   ← visible_content/completion_status-Mapping für Endzustände
├── executor.py       ← Einzelschritt-Ausführung
└── reflection.py     ← Entscheidung nach jedem Schritt
```

---

## Dateien

### `task_loop.py`
Einstiegspunkt. Nimmt den `ThinkingPlan` entgegen, startet den Runner, gibt `TaskLoopResult` zurück.
Stellt auch `continue_task_loop()` bereit wenn der User nach einem WAITING-State weitermacht.
Enthält schlanke Start-/Resume-/Replan-Verdrahtung:

- `start_task_loop()` baut den initialen `TaskLoopSnapshot`
- `continue_task_loop()` setzt einen `WAITING`-Snapshot fort oder setzt `CANCELLED`
- `_run_with_replanning()` koppelt `REPLANNING` kontrolliert an `core/thinking/replanner.py`
- `objective` wird nie aus Step-Daten rekonstruiert

**Max 80 Zeilen.**

### `contracts.py`
Alle Datenstrukturen: `TaskLoopSnapshot`, `TaskLoopResult`, `TaskLoopState`, `StopReason`, `RiskLevel`.
State Machine mit validierten Transitionen — übernommen und bereinigt aus dem alten Code.
Importiert **nichts** aus dem eigenen Modul — nur stdlib.
**Max 150 Zeilen.**

```python
class TaskLoopState(Enum):
    EXECUTING  = "executing"
    REFLECTING = "reflecting"
    REPLANNING = "replanning"    # Übergibt an Thinking.replanner
    COMPLETED  = "completed"
    WAITING    = "waiting"      # Wartet auf User-Input
    BLOCKED    = "blocked"      # Harter Stopp
    CANCELLED  = "cancelled"

class StopReason(Enum):
    MAX_STEPS_REACHED    = "max_steps_reached"
    STEP_FAILED          = "step_failed"
    RISK_GATE_REQUIRED   = "risk_gate_required"
    USER_DECISION_NEEDED = "user_decision_needed"
    NO_PROGRESS          = "no_progress"
    USER_CANCELLED       = "user_cancelled"

@dataclass(frozen=True)
class TaskLoopSnapshot:
    plan_id: str
    conversation_id: str
    objective: str                  # Originaler User-Prompt / Arbeitsauftrag
    state: TaskLoopState
    current_step_index: int
    max_steps: int                  # vom Aufrufer/Config gesetzt, nicht hardcodiert
    max_retries_per_step: int       # vom Aufrufer/Config gesetzt, nicht hardcodiert
    completed_steps: List[str]
    pending_step: str
    artifacts: List[Dict[str, Any]]
    stop_reason: Optional[StopReason]
    error_count: int
    retry_counts: Dict[str, int]
    progress_signature: str
    no_progress_count: int

@dataclass(frozen=True)
class TaskLoopResult:
    state: TaskLoopState
    stop_reason: Optional[StopReason]
    artifacts: List[Dict[str, Any]]  # Ergebnisse aller Schritte
    visible_content: str             # Was der User sieht
    snapshot: TaskLoopSnapshot       # Für continue-Flows
```

### Budget-Modell

Task-Loop-Budgets sind Teil des Contracts und kommen von außen.
Sie werden nicht in `runner.py`, `reflection.py` oder einem späteren Replanner
hart codiert.

Aktuell implementiert:

- `max_steps`
- `max_retries_per_step`
- `replan_count`
- `max_replans`

Warum getrennt:

- **Retry** bedeutet: derselbe Schritt wird noch einmal versucht.
- **Replan** bedeutet: Thinking darf den Plan strukturell neu aufbauen.

Das sind unterschiedliche Budgets und dürfen nicht implizit über dasselbe Limit
gesteuert werden.

Zielregel:

- Wenn Retry-Budget erschöpft ist, darf der Loop `REPLANNING` anfordern.
- Ob danach wirklich neu geplant wird, hängt zusätzlich vom extern gesetzten
  Replan-Budget ab.
- Wenn `replan_count >= max_replans`, wird nicht weiter eskaliert, sondern
  kontrolliert mit `REPLAN_BUDGET_EXHAUSTED` gestoppt.

Konfigurationsregel:

- Defaults kommen aus Config bzw. Runtime-Settings.
- Aktueller Core-Pfad liest diese Werte über `config.pipeline.loop_engine` ein.
- Die Admin-API exponiert sie unter `/settings/sequential/runtime`.
- Eine eigene WebUI-Oberfläche dafür ist noch nicht umgesetzt.
- Später darf die WebUI diese Budgets unter `Task Loop` einstellen.
- Der Contract bleibt dieselbe Quelle der Wahrheit; die UI ist nur eine
  Oberfläche dafür.

### Completion-Contract

Jeder `PlanStep` kann maschinenlesbare Abnahmekriterien tragen:

- `done_when: str` — Kriterium für „Ziel erreicht", z. B. `"file_created"`, `"exit_code:0"`,
  `"stdout_contains:PASSED"`. Leerer String = heutiges Verhalten (Step-SUCCESS = fertig).
- `required_evidence: List[str]` — Liste geforderter `artifact_type`-Werte,
  die `outcome_evaluator` gegen die gesammelten Artifacts prüft.

Auswertung durch `outcome_evaluator.py` (deterministisch, kein LLM).
Beide Felder sind optional mit Default — alle bestehenden `PlanStep`-Konstruktoren
bleiben valide.

#### Capability-Gap BLOCK

Wenn ein `required_evidence`-Typ durch kein registriertes Tool erzeugt werden kann,
gibt `outcome_evaluator` `BLOCK` mit `StopReason.CAPABILITY_GAP` zurück, statt
zu replanennen. Injektions-Pfad:

```
task_loop_stage.py (available_tools → available_evidence_types: frozenset[str])
  → start_task_loop(available_evidence_types)
  → _run_with_replanning(available_evidence_types)
  → run_task_loop_with_outcome(available_evidence_types)
  → finalize_completion(available_evidence_types)
  → outcome_evaluator.evaluate(available_evidence_types)
```

`available_evidence_types` ist ein `frozenset[str]` aller `capability_evidence_types`
der registrierten Tools. Überall Default `frozenset()` — Backward-Compat ist gewährleistet.

Siehe `docs/implementation-plans/completed/51-taskloop-objective-completion.md` (Phase 5) für den vollständigen Plan.

---

### Objective-Erhaltung

Der originale User-Prompt bzw. Arbeitsauftrag ist Teil des Task-Loop-Contracts.
Er darf im Loop niemals aus `step.title`, `goal`, Tool-Argumenten oder einem
normalisierten Plan rekonstruiert werden.

Pflichtregel:

- `TaskLoopSnapshot.objective` enthält den ursprünglichen Arbeitsauftrag.
- `start_task_loop()` übernimmt `objective` aus dem validierten Plan-/Request-Kontext.
- `continue_task_loop()` darf neuen User-Text ergänzen, aber `objective` nicht
  ersetzen.
- Retry, Resume, WAITING-Fortsetzung und Re-Planning reichen immer
  `objective + snapshot + failed_step + artifacts` weiter.
- `runner.py`, `reflection.py` und `executor.py` dürfen Entscheidungen nie nur
  aus Step-Titeln ableiten.

Warum: Wenn der ursprüngliche Prompt im Loop oder beim Restart verloren geht,
bleiben nur kurze Step-Namen wie `Container deployen` übrig. Daraus entstehen
Drift, falsche Tool-Argumente und Halluzinationen. Der Loop muss deshalb den
vollständigen Auftrag als unverlierbaren Snapshot-Kontext tragen.

### `runner.py`
Der eigentliche Vorwärtslauf.
Iteriert über die `PlanStep`-Liste von Thinking, ruft pro Schritt `executor.py` auf,
dann `reflection.py` — und entscheidet ob weiter, fertig oder Fehler.
Kein LLM-Call, keine Container-Logik.
**Max 150 Zeilen.**

```
runner.py Ablauf:
  for step in plan.steps:
      result = executor.run(step)
      decision = reflection.evaluate(result, snapshot)
      if decision == CONTINUE  → nächster Schritt
      if decision == COMPLETED → fertig → Output
      if decision == WAITING   → warten auf User
      if decision == REPLAN    → sichtbar als `REPLANNING`, Hook zu Thinking
      if decision == BLOCK     → sofort stoppen
```

Aktueller Stand:

- `SUCCESS` führt zu nächstem Schritt oder `COMPLETED`
- `SKIPPED` führt zu `WAITING`
- erschöpftes Retry-Budget führt zu `REPLANNING`
- `replan_count` wird beim Übergang nach `REPLANNING` erhöht
- `task_loop.py` ruft bei `REPLANNING` optional `core/thinking/replanner.py` auf
- replante Pläne laufen mit erhaltenem `objective`, `artifacts` und `replan_count` weiter
- ausgeschöpftes Replan-Budget führt zu `BLOCKED`
- `MAX_STEPS_REACHED` und `NO_PROGRESS` führen zu `BLOCKED`
- vorhandene `artifacts` werden über Resume weitergetragen

### `presentation.py`
Reine Darstellungs-Ableitung für Task-Loop-Endzustände, ausgelagert aus `runner.py`
(verhaltensneutral, P11 SP0):

- `visible_content_for(state, step_title, reason)` — Nutzertext zum Endzustand
- `completion_status_for(state)` — `CompletionStatus` zum Endzustand

Trifft selbst keine Entscheidung, kein LLM-Call. Liest nur bereits getroffene
Reflection-Entscheidungen aus `runner.py`.

### `executor.py`
Führt einen einzelnen `PlanStep` aus.
Ruft den Tool Executor (`tools/`) mit den Parametern des Schritts auf.
Gibt ein strukturiertes Ergebnis zurück — Erfolg, Fehler oder Timeout.
Keine Planungs-Logik, keine Container-spezifischen Policies.
**Max 150 Zeilen.**

### `reflection.py`
Wird nach jedem abgeschlossenen Schritt von `runner.py` aufgerufen.
Entscheidet deterministisch (kein LLM): was passiert als nächstes?

| Situation | Entscheidung |
|-----------|--------------|
| Schritt OK, nächster Schritt vorhanden | CONTINUE |
| Alle Schritte fertig | COMPLETED |
| Schritt fehlgeschlagen, retry möglich | CONTINUE (retry) |
| Schritt fehlgeschlagen, kein retry | REPLAN → Thinking |
| Retry erschöpft und Replan-Budget erschöpft | BLOCK |
| Risiko-Gate erkannt | WAITING |
| Max Steps / No Progress | BLOCK |

Kein LLM-Call — nur Zustandsauswertung.
**Max 150 Zeilen.**

---

## Regeln

- **Max 200 Zeilen pro Datei** — wird eine Datei größer, wird sie aufgeteilt
- **Kein LLM-Call im Task Loop** — weder in runner.py noch in reflection.py noch in executor.py
- **Kein action_resolution-Sub-System** — Thinking hat die Actions bereits geplant
- **Keine Container-Logik** — gehört in Tool Executor (`tools/`)
- **9 Policy-Files → 1 reflection.py** — alle Stop-Entscheidungen an einem Ort
- **Re-Planning geht zu Thinking** — `core/thinking/replanner.py`, nicht intern
- **Re-Planning ist sichtbar** — `TaskLoopState.REPLANNING` ist ein eigener State
- **Snapshot ist immutable** — jeder Zustandswechsel erzeugt einen neuen Snapshot via `replace()`
- **Objective bleibt erhalten** — `TaskLoopSnapshot.objective` wird bei jedem Übergang weitergereicht
- **Budgets kommen von außen** — `max_steps`, `max_retries_per_step` und `max_replans` werden im Snapshot bzw. Request-Kontext getragen, nicht in Reflection hardcodiert
- **`contracts.py` ist das Fundament** — wird zuerst geschrieben, danach nichts mehr daran ändern ohne Review

---

## State Machine

```
                    ┌─────────────────────────────┐
                    │                             │
              EXECUTING ──────────────────► REFLECTING
                    │                             │
                    │            ┌────────────────┤
                    │            ↓                │
                    │        COMPLETED            │
                    │             REPLANNING ◄────┤
                    │                 │           ↓
                    │                 └────► EXECUTING
                    └───────────────────────► WAITING
                                                  │
                                             BLOCKED
                                                  │
                                            CANCELLED
```

---

## Zwei Einstiegspunkte

| Aufrufer | Funktion | Input |
|----------|----------|-------|
| Control-Verifier / Pipeline (neuer Loop) | `task_loop.py → start_task_loop()` | ThinkingPlan |
| User (nach WAITING) | `task_loop.py → continue_task_loop()` | TaskLoopSnapshot + User-Text |

---

## Abhängigkeiten

```
task_loop.py
  └── runner.py
        ├── executor.py
        │     ├── contracts.py
        │     └── tools/ (Tool Executor)
        ├── reflection.py
        │     └── contracts.py
        ├── presentation.py
        │     └── contracts.py
        └── contracts.py

Bei REPLAN:
  runner.py → core/thinking/replanner.py
```

---

## Was der Task Loop NICHT macht

- Kein LLM-Call
- Kein action_resolution-Sub-System
- Keine Container-spezifischen Policies
- Kein Re-Planning intern — geht immer zu Thinking
- Keine 9 Policy-Files
- Keine Tool-Auswahl — die Tools stehen bereits im PlanStep von Thinking
