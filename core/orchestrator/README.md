# Orchestrator

Wird primaer aktiviert wenn der Control-Classifier `needs_orchestrator = True` meldet.
Bereitet alles vor was Thinking braucht: passende Tools und relevanter Kontext.

**Einzige Aufgabe:** Tools auflösen + Kontext bauen + beides verpackt an Thinking übergeben.

---

## Status

- ✅ `contracts.py` implementiert
- ✅ `orchestrator.py`, `tools.py`, `context.py`, `resolver.py` minimal implementiert
- ✅ `tool_candidates/` liefert jetzt einen kleinen Top-K Kandidatenpfad aus MCP-Intent-Metadaten
- ✅ vor dem Ranking greift jetzt ein erster Capability-Constraint-Pfad fuer Container-Runtime-Operationen
- ✅ direkte Informationsfragen koennen bei starkem Intent-Match ebenfalls `selected_tools` erhalten
- ✅ Baseline-Tests in `tests/test_orchestrator_minimal.py`
- ✅ `conversation_meta` und `conversation_policy` werden im Shadow Mode in den Context eingebaut
- ✅ erster Scope-Filter im Kontextpfad aktiv: disallowte Kontextquellen werden vor dem Source-Call geblockt
- ✅ erstes Long-Term-Write-Enforcement sitzt jetzt im SQL-Memory-MCP
- 🔶 `core/pipeline/runner.py` ruft den Orchestrator im komplexen Pfad bereits auf; fuer installierte MCP-Intents gibt es zusaetzlich einen kleinen Kandidatenpfad im Direktmodus
- ✅ Admin-API speist Default-Sources (`memory`, `conversation_meta`, `runtime`, `active_containers`) ein — siehe [[05-adapters#Orchestrator-Context-Sources|Adapters → Orchestrator-Context-Sources]]
- ⏳ feingranulares Retrieval-Filtering innerhalb einzelner Memory-Backends folgt
- ✅ `active_containers` kann jetzt einen verifizierten `home_context` fuer `trion-home` liefern
- ✅ Capability-/Scope-Fragen mit aktivem Container-/Home-Kontext bleiben jetzt toolseitig leer und werden spaeter aus verifiziertem Scope-Kontext statt aus `container_inventory` beantwortet
- ⏳ weitere Quellen (`workspace`) sind vorbereitet (`_SOURCE_NAMESPACE_MAP`), aber noch nicht im Default-Source-Bundle

---

## Modulstruktur

```
core/orchestrator/
├── orchestrator.py             ← Einstiegspunkt
├── contracts.py                ← Datenstrukturen
├── tools.py                    ← Tool-Auswahl (select_relevant_tools, list_available_tools)
├── tool_descriptor_projection.py ← roh → ToolDescriptor + Eligibility-Predicate (P11.0 SP4)
├── tool_filter.py              ← Allow-/Blocklist + forbidden_direct-Ausschluss
├── frame_signals.py            ← Signal-Extraktion aus routing_frame (live_claim, dialogue_signal)
├── tool_eligibility.py         ← Contract-vs-ToolDescriptor-Gate
├── tool_eligibility_helpers.py ← kleine Eligibility-/Legacy-Projektionshelper
├── tool_candidates/            ← Top-K Kandidaten aus Tool-Intent-Metadaten
├── context.py                  ← Kontext-Aufbau
└── resolver.py                 ← Finale Zusammenführung
```

---

## Dateien

### `orchestrator.py`
Einstiegspunkt. Ruft `resolver.py` auf und gibt das `OrchestratorPackage` zurück.
Enthält **keine eigene Logik** — nur Verdrahtung.
**Max 80 Zeilen.**

### `contracts.py`
Alle Datenstrukturen: `OrchestratorPackage`.
Importiert **nichts** aus dem eigenen Modul — nur stdlib und `core/classifier/contracts.py`.
**Max 80 Zeilen.**

```python
@dataclass
class OrchestratorPackage:
    available_tools: List[str]           # Alle verfügbaren Tools
    selected_tools: List[str]            # Tools die zur Anfrage passen
    context: Dict[str, Any]              # Memory, Workspace, Container-Status
    classifier_result: ClassifierResult  # Durchgereicht vom Classifier
```

### `tools.py`
Zwei Aufgaben — sauber getrennt in zwei Funktionen:
1. `list_available_tools()` projiziert rohe Tool-Eintraege ueber `tool_descriptor_projection.py::descriptor_from_raw()` zu `ToolDescriptor`
2. `select_relevant_tools()` waehlt relevante Tools fuer diese Anfrage aus
   (basierend auf `routing_frame["operation_contract"]`, `ToolDescriptor`-
   Metadaten und MCP-Intent-Metadaten)

Keine Kontext-Logik, keine Callback-Parameter-Kaskaden.
**Max 150 Zeilen.**

### `tool_descriptor_projection.py`
P11.0 SP4: aus `tools.py` ausgelagert. Enthaelt `is_eligible_tool_intent()` (einzige Eligibility-Predicate fuer Registry-Mirror-Eintraege, fail-closed) und `descriptor_from_raw()` (roh → `ToolDescriptor`, ruft dieselbe Predicate als zusaetzlichen Guard auf, inkl. Namensbindung zwischen `tool_intent.name` und Toolname). **Max 150 Zeilen.**

### `tool_filter.py`
Filtert `ToolDescriptor`-Listen nach Allowlist, Blocklist und `tool_role`:
Tools mit `tool_role == "forbidden_direct"` werden immer von der Planung
ausgeschlossen (Doc 36 Regel 3). **Max 60 Zeilen.**

### `frame_signals.py`
Liest `live_claim` und `dialogue_signal` aus `routing_frame["source_signals"]`. Kein Tool-Auswahl-Code, keine Capability-Logik — nur Signal-Extraktion mit Fallback fuer Pfade ohne Pipeline-Kontext.
Exportiert: `live_claim_from_frame`, `dialogue_signal_from_frame`. **Max 60 Zeilen.**

### `tool_eligibility.py`
Contract-vs-ToolDescriptor-Gate fuer `T_eligible`: Domain, Operation, Evidence,
Scope und Risiko als harte Gates. Kein Rohtext-Fallback, keine zweite
Operationsberechnung.

### `tool_eligibility_helpers.py`
Kleine gemeinsame Helper fuer Operation-Family-Normalisierung, Zielscope-
Projektion und Legacy-Projektionen, die noch von Tests/Taxonomie-Locks
abgedeckt werden.

### `tool_candidates/`
Kleines Untermodul fuer generische Kandidatenfindung.

- `contracts.py` — kleine Ranking-Datenstruktur
- `scoring.py` — lexical scorer ueber `description`, `examples`, `keywords`
- `embedding.py` — optionaler Embedding-Score; technische Ausfaelle bleiben `unavailable` und werden nicht als echter Negativ-Match behandelt
- `service.py` — kombiniert lexical + semantic und liefert `top_k` Kandidaten in Reihenfolge

Vor dem Ranking: Intent-/Claim-Klasse und Capability-Constraints begrenzen den erlaubten Toolraum hart; Embedding ist nur noch Ranking-Signal innerhalb erlaubter Kandidaten; degradierter lexical-only Mode darf keine mutierenden Runtime-Tools in Read-only-Faellen hochziehen.

Spezialfall ohne MCP-Sonderwissen: Capability-/Scope-Fragen wie `was kannst du in diesem Container tun?` werden nicht als `container_inventory` beantwortet — der Orchestrator behandelt sie als Scope-/Capability-Frage, die Hauptwahrheit dafuer kommt aus verifiziertem Kontext wie `home_context.available_capability_classes`.

Wichtig: keine MCP-Sonderfaelle, keine globale Keywordliste als operative Wahrheit im Core. Daten kommen aus dem Registry-Mirror (P11.0), nicht direkt aus dem Bundle — `tool_intents.json` ist die Authoring-Quelle, der Installer projiziert sie beim Install/Update in den Mirror; siehe [[21-mcp-installer|MCP-Installer]].

### `context.py`
Baut den Kontext-Block für Thinking:
- Memory-Einträge (falls vorhanden)
- Workspace-Status
- Aktive Container
- ConversationMeta + effektive Conversation-Policy (Shadow Mode)

Aktueller Policy-Schritt:

- bekannte Kontextquellen werden auf Scope-Namespaces gemappt
- `memory.mode=conversation_only|disabled` blockiert globale Memory-Quellen vor dem Aufruf
- siloed Scopes blockieren nicht erlaubte Quellen bereits im Orchestrator-Kontextpfad
- unklassifizierte Quellen bleiben vorerst erlaubt und werden nur sichtbar markiert

Jede Kontext-Quelle ist eine eigene Funktion. Keine Tool-Logik.
**Max 150 Zeilen.**

### `resolver.py`
Kombiniert `tools.py` und `context.py` zum fertigen `OrchestratorPackage`.
Entscheidet was wirklich gebraucht wird — überspringt Kontext-Quellen die nicht relevant sind.
**Max 150 Zeilen.**

---

## Regeln

- **Max 200 Zeilen pro Datei** — wird eine Datei größer, wird sie aufgeteilt
- **Kein autonomer Loop** — der Orchestrator hat keine eigene State Machine
- **Keine Ton-Klassifikation** — gehört nicht hier hin
- **Keine Callback-Kaskaden** — Funktionen haben max 5 Parameter
- **Tool-Auflösung und Kontext-Aufbau sind strikt getrennt** — `tools.py` kennt `context.py` nicht
- **Kein hardcodierter Text** — Tool-Auswahl-Regeln kommen aus `intelligence_modules`
- **`contracts.py` ist das Fundament** — wird zuerst geschrieben, danach nichts mehr daran ändern ohne Review

---

## Output

```python
OrchestratorPackage(
    available_tools=["deploy_container", "list_blueprints", "get_secrets", ...],
    selected_tools=["deploy_container", "list_blueprints"],
    context={
        "conversation_meta": {...},
        "conversation_policy": {...},
        "memory": [...],
        "workspace": {...},
        "active_containers": [...]
    },
    classifier_result=ClassifierResult(...)
)
```

---

## Abhängigkeiten

```
orchestrator.py
  └── resolver.py
        ├── tools.py
        │     └── contracts.py
        └── context.py
              └── contracts.py

MCP-Intent-Metadaten:
  adapters/tool_runner_bridge.py
    └── reichert `hub.list_tools()` mit `tool_intent` aus der Runtime-Registry an
```

---

## Was der Orchestrator NICHT macht

- Keine Ton-Klassifikation
- Keine Query-Budget-Berechnung
- Keine Domain-Routing-Logik
- Keine eigene State Machine oder autonomer Loop
- Keine Skill-Code-Generierung
- Kein direkter LLM-Call
- Noch kein feingranulares Filtering innerhalb einzelner Retrieval-Quellen
