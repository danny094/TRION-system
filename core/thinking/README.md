# Thinking

Analysiert den User-Input und erstellt einen strukturierten Plan mit konkreten Schritten.
Wird von Classifier direkt (einfache Anfragen) oder vom Orchestrator (komplexe Anfragen) aufgerufen.
Bei Task Loop Fehlern übernimmt Thinking auch das Re-Planning.

**Einzige Aufgabe:** Verstehen was gefragt ist und einen ausführbaren Plan erstellen.

---

## Status

- ✅ `contracts.py` implementiert
- ✅ `thinking.py` verdrahtet jetzt `analyzer/ -> planner/`
- ✅ `analyzer/`, `planner/`, `prompts.py` minimal implementiert
- ✅ `replanner.py` nutzt denselben Analyzer-/Planner-Pfad
- 🔶 LLM-Analyzer ist vorhanden, aber standardmäßig per Config noch deaktiviert
- ✅ Fallback-Analyzer ist klassifier-aware: liest `Category` und `matched_pattern` aus dem `ClassifierResult`, übernimmt Memory-Items aus dem Orchestrator-Kontext, liefert differenzierte `hallucination_risk`/`task_loop_kind`/`task_loop_reason`/`reasoning_type`
- ✅ `thinking.py` akzeptiert jetzt optional Orchestrator-Kontext
- ✅ komplexer Pipeline-Pfad reicht Orchestrator-Kontext an Thinking weiter
- ✅ Analyzer nutzt einen kleinen, kontrollierten Teil dieses Kontextes
- ✅ Prompt-seitige Kontextverdichtung und harte Char-Grenzen sind eingebaut
- ✅ `document_context` wird jetzt als eigener Prompt-Block an den Analyzer weitergereicht
- ✅ Planner kann erste dokumentbezogene Retrieval-Schritte gegen Chunk-Pointer bauen
- ✅ produktive Tool-Verfuegbarkeit fuer `workspace_get` / `memory_semantic_search` kann jetzt aus dem Dokumentpfad eingespeist werden
- ✅ Dokument-Retrieval ist jetzt intent- und toolreihenfolgebasiert verfeinert
- ✅ Strukturfragen koennen jetzt auf `preferred_entry_ids` / Inhaltsverzeichnis-Kandidaten statt auf einzelne harte Chunks planen
- ✅ semantische Suchtreffer koennen jetzt spaetere `workspace_get`-Schritte ueber `workspace_entry_id` produktiv steuern
- ✅ Fallback-Analyzer behaelt `document_tool_mode` fuer `structure_first` vs. `semantic_first` jetzt durch den Pfad
- ✅ Fallback-Analyzer leitet `workspace_first`, `workspace_only`, `structure_first`, `semantic_first` und `exact_lookup` jetzt konsistenter aus Frageart und Tool-Set ab
- 🔶 Offene Feinarbeit und produktiver Gesamtstatus fuer den Dokumentpfad: siehe [[16-long-input-document-routing|Long Input & Document Routing]]

---

## Modulstruktur

```
core/thinking/
├── thinking.py     ← Einstiegspunkt
├── contracts.py    ← Datenstrukturen
├── analyzer/       ← Verdrahtung LLM-Call vs. Fallback (Package)
├── analyzer_io.py  ← Prompt-Invoke + JSON-Parsing
├── fallback/       ← deterministischer Fallback, klassifier-aware (Package)
├── planner/        ← Schritt-Strukturierung (Package)
├── replanner.py    ← Re-Planning bei Fehlern
└── prompts.py      ← Prompt-Aufbau
```

---

## Dateien

### `thinking.py`
Einstiegspunkt. Ruft `analyzer/` auf, übergibt das Ergebnis an `planner/` und gibt den fertigen `ThinkingPlan` zurück.
Enthält **keine eigene Logik** — nur Verdrahtung.
**Max 80 Zeilen.**

Nächster Anschluss:

- `thinking.py` nimmt im komplexen Pfad optional Orchestrator-Kontext entgegen
- relevante Teile davon werden kontrolliert an `analyzer.py` weitergereicht
- Fallback ohne Kontext und ohne LLM bleibt kompatibel

### `contracts.py`
Alle Datenstrukturen: `ThinkingPlan`, `PlanStep`, `RiskLevel`.
Importiert **nichts** aus dem eigenen Modul — nur stdlib.
Wird von allen anderen Dateien importiert, importiert selbst niemanden.
**Max 100 Zeilen.**

```python
@dataclass
class ThinkingPlan:
    intent: str                    # Was der User will
    steps: List[PlanStep]          # Konkrete Ausführungsschritte
    needs_task_loop: bool          # True wenn multi-step
    risk_level: RiskLevel          # Gesamtrisiko des Plans
    reasoning: str                 # Begründung
    suggested_tools: List[str]     # Benötigte Tools
    context_hints: Dict[str, Any]  # Hinweise für Output Layer

@dataclass
class PlanStep:
    step_id: str
    title: str
    goal: str
    tool: Optional[str]   # Tool das für diesen Schritt gebraucht wird
    risk: RiskLevel

class RiskLevel(Enum):
    SAFE = "safe"
    NEEDS_CONFIRMATION = "needs_confirmation"
    BLOCK = "block"
```

### `analyzer/`
Verdrahtungsschicht (Package): entscheidet anhand `THINKING_ANALYZER_ENABLE`, ob der
LLM-Pfad oder der deterministische Fallback genommen wird. Bei aktivem
LLM-Pfad ist der Call in `__init__.py` der einzige LLM-Aufruf des gesamten Moduls.
Schlägt der LLM-Call fehl, wird kontrolliert auf `fallback/` zurückgefallen.
Akzeptiert optional: `available_tools`, `selected_tools`, reduzierten
`orchestrator_context`, `document_context`, `replan_context`.
Submodule: `helpers.py` (routing_frame-Helfer), `normalizers.py` (Plan-Normalisierung).
**Max 200 Zeilen gesamt.**

### `fallback/`
Deterministischer Analyse-Pfad ohne LLM-Call (Package). Liest
`ClassifierResult.category`/`matched_pattern` und Memory-Items aus dem
Orchestrator-Kontext und liefert differenzierte Signale:

- `hallucination_risk`: `high` für `RISK`, `medium` für `TOOL`/`PLANNING`/`UNKNOWN`-mit-Tools, sonst `low`
- `task_loop_kind`: `visible_multistep` (mehrere Tools), `single_tool`, `narrated_plan` (PLANNING ohne Tools) oder `none`
- `task_loop_reason`: erklärt warum (oder warum nicht) der Task-Loop greift
- `needs_memory`: kombiniert Keyword-Heuristik und vorhandene Memory-Items aus dem Orchestrator
- `reasoning`: nennt Classifier-Pattern, resolved Tools und Memory-Verfügbarkeit

Submodule: `tools.py`, `task_loop.py`, `reasoning.py`, `hallucination_risk.py`, `memory_signal.py`.
**Max 200 Zeilen pro Submodul.**

### `planner/`
Nimmt den rohen Plan von `analyzer/` und strukturiert daraus konkrete `PlanStep`-Objekte (Package).
**Kein LLM-Call** — nur deterministische Logik.
Entscheidet ob `needs_task_loop = True` (Tool nötig).
Submodule: `frame_reader.py`, `plan_meta.py`, `step_builder.py`, `tool_resolver.py`.
**Max 200 Zeilen gesamt.**

### `replanner.py`
Wird vom Task Loop aufgerufen wenn ein Schritt fehlschlägt.
Aktueller Stand:

- übernimmt `objective`, `failed_step`, Fehlerstatus und vorhandene `artifacts`
- reicht diese Daten als `replan_context` an `analyzer/` weiter
- baut über `planner/` einen neuen `ThinkingPlan`
- schreibt den Replan-Kontext zusätzlich in `context_hints["replan"]`
**Max 100 Zeilen.**

### `prompts.py`
Baut alle Prompts aus `intelligence_modules` zusammen.
Kein hardcodierter Prompt-Text im Code — alles aus den Prompt-Templates und CSVs.
Injiziert Ability Injectors, Cognitive Priors und Procedural Rules aus intelligence_modules.
**Max 150 Zeilen.**

Nächster Schritt:

- Dokumentpfad-Status und offene Retrieval-Feinarbeit: siehe [[16-long-input-document-routing|Long Input & Document Routing]]
- naechster lokaler Code-Schritt: weitere dokumentbezogene Helfer klein und getrennt halten

---

## Regeln

- **Max 200 Zeilen pro Datei** — wird eine Datei größer, wird sie aufgeteilt
- **Nur ein LLM-Call im gesamten Modul** — in `analyzer/`, nirgendwo sonst
- **`planner/` macht keinen LLM-Call** — nur deterministische Schritt-Strukturierung
- **Kein Import aus `task_loop`** — Thinking kennt den Task Loop nicht
- **Kein hardcodierter Prompt-Text** — alles aus `intelligence_modules`
- **`contracts.py` ist das Fundament** — wird zuerst geschrieben, danach nichts mehr daran ändern ohne Review
- **Re-Planning ist kein Sonderfall** — `replanner.py` nutzt dieselbe `analyzer/`, nur mit mehr Kontext
- **Tool-Timeouts bleiben pro Schritt möglich** — `PlanStep.timeout_s` kann langsame Tools wie Container-Deploys explizit höher setzen

---

## Output

```python
ThinkingPlan(
    intent="deploy_container",
    steps=[
        PlanStep(step_id="1", title="Blueprint validieren", goal="...", tool="validate_blueprint", risk=RiskLevel.SAFE),
        PlanStep(step_id="2", title="Container deployen",   goal="...", tool="deploy_container",   timeout_s=180.0, risk=RiskLevel.NEEDS_CONFIRMATION),
        PlanStep(step_id="3", title="Status prüfen",        goal="...", tool="get_container_status", risk=RiskLevel.SAFE),
    ],
    needs_task_loop=True,
    risk_level=RiskLevel.NEEDS_CONFIRMATION,
    reasoning="Container-Deploy braucht Blueprint-Validierung und anschließende Verifikation.",
    suggested_tools=["validate_blueprint", "deploy_container", "get_container_status"],
    context_hints={"response_style": "step_by_step", "show_progress": True}
)
```

---

## Abhängigkeiten

```
thinking.py
  ├── analyzer/
  │     ├── contracts.py
  │     ├── prompts.py
  │     ├── fallback/    ← deterministischer Pfad ohne LLM
  │     └── core/llm_provider_client.py
  ├── planner/
  │     └── contracts.py
  └── contracts.py

replanner.py (separater Einstiegspunkt für Task Loop)
  ├── analyzer/
  └── contracts.py

intelligence_modules (nur lesend):
  ├── prompts/layers/thinking*
  ├── executable_rag/ability_injectors_v2.csv
  ├── knowledge_rag/cognitive_priors_v2.csv
  ├── procedural_rag/causal_reasoning_procedures_v2.csv
  └── cim_skill_rag/execution_mode_signals_v2.csv
```

---

## Zwei Einstiegspunkte

| Aufrufer | Funktion | Input |
|----------|----------|-------|
| Classifier / Orchestrator | `thinking.py` | User-Text + OrchestratorPackage |
| Task Loop (bei Fehler) | `replanner.py` | User-Text + fehlgeschlagener Schritt + Hint |
