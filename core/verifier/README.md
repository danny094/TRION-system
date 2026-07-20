# Control-Verifier

Prüft den von Thinking erstellten Plan bevor er ausgeführt wird.
Wird genau einmal aufgerufen — nach Thinking, vor Output oder Task Loop.

**Einzige Aufgabe:** Plan prüfen und ein eindeutiges Verdict zurückgeben.

---

## Status

- ✅ `contracts.py` implementiert
- ✅ `verifier.py` verdrahtet `input_prepare -> safety -> llm_check`
- ✅ `input_prepare.py` bereitet Long-Document-Inputs kontrolliert fuer den Verifier vor
- ✅ `safety.py` ist jetzt nur noch schlanke Verdrahtung fuer deterministische Checks
- ✅ `rule_loader.py` laedt Verifier-Regeln aus `intelligence_modules` mit kleinem CSV-/mtime-Cache
- ✅ `policy_checks.py` wertet Security-Policies und kausale Anti-Patterns regelgetrieben aus
- ✅ `plan_checks.py` prueft deterministisch Plan-Qualitaet und Vorbedingungen fuer operative und mutierende Tool-Schritte
- ✅ `approval_checks.py` prueft deterministisch, ob riskante Tool-Schritte einen expliziten `approval_request`-Schritt brauchen
- ✅ `document_checks.py` kapselt dokumentbezogene Retrieval-Regeln getrennt vom restlichen Safety-Pfad
- ✅ `input_prepare.py` reicht fuer Long-Document-Inputs jetzt auch Retrieval-Hinweise wie `workspace_entry_ids`, Kandidatenlisten und `document_retrieval_mode` weiter
- ✅ `input_prepare.py` leitet fuer Long-Document-Inputs jetzt auch `question_focus` und `structure_required` fuer den Verifier ab
- ✅ `input_prepare.py` reicht fuer Long-Document-Inputs jetzt auch einen kompakten `retrieval_plan` mit Search-Schritten, direkten Reads und search-driven Reads weiter
- ✅ dokumentbezogene Retrieval-Plaene werden jetzt deterministisch abgelehnt, wenn Reads ausserhalb des bekannten Dokumentkontexts liegen, Suchschritte fehlen oder Retrieval-Modi widerspruechlich geplant sind
- ✅ operative Planregeln fuer `deploy_container`, `exec_in_container`, `stop_container`, `blueprint_*` und exakte Dokument-Lookups sind jetzt CSV-getrieben
- ✅ Mutationsregeln fuer `workspace_*`, `conversation_meta_upsert` und `secret_delete` sind jetzt CSV-getrieben
- ✅ Approval-Regeln fuer `deploy_container`, `exec_in_container`, `blueprint_delete` und `secret_delete` bei `needs_confirmation` sind jetzt CSV-getrieben
- ✅ `llm_check.py` und `prompts.py` bilden den produktiven Control-Pfad ab
- ✅ der Verifier-Prompt traegt jetzt auch kompakte Retrieval-Signale wie `retrieval_mode`, bekannte `workspace_entry_ids`, Kandidatenlisten und den verdichteten `retrieval_plan` in den optionalen LLM-Check
- ✅ die Prompt-Layer `control`, `control_verify_input` und `control_verify_plan` trennen jetzt `semantic_first`, `structure_first` und `exact_lookup/workspace_first` ausdruecklich
- ✅ der LLM-Check kann jetzt ueber `CONTROL_LLM_CHECK_LONG_DOCUMENT_ENABLE` gezielt nur fuer Long-Document-Inputs aktiviert werden
- ✅ der LLM-Check kann jetzt zusaetzlich ueber `CONTROL_LLM_CHECK_MODES` kontrolliert fuer `long_document`, `task_loop`, `needs_confirmation` oder `all` ausgerollt werden
- ✅ Long-Document-Inputs nutzen im optionalen LLM-Check jetzt den bestehenden `deep`-Pfad fuer Timeout und Endpoint-Override
- ✅ `llm_check.py` normalisiert jetzt widerspruechliche APPROVED-Warnings schmal nach `question_focus`
- ✅ ungueltige, unvollstaendige oder widerspruechliche JSON-Entscheidungen aus dem LLM-Check werden jetzt als `REJECTED` statt als stilles `APPROVED` behandelt
- ✅ Verifier-Testabdeckung fuer Input, LLM-Check, Safety, Plan-Checks und Mutationsregeln ist gruen
- 🔶 der semantische PREGO-Fall ist jetzt deutlich konsistenter; offene Feinarbeit liegt vor allem noch bei spaeterer Prompt-Schaerfung und zusaetzlichen Retrieval-Artefakten
- 🔶 `CONTROL_LLM_CHECK_ENABLE=false` per Default; LLM-Pruefung ist eingebaut, aber noch nicht standardmaessig aktiv

---

## Modulstruktur

```
core/verifier/
├── verifier.py    ← Einstiegspunkt
├── contracts.py   ← Datenstrukturen
├── input_prepare.py ← Verifier-Input fuer normal vs. long-document
├── safety.py      ← Verdrahtet deterministische Checks
├── document_checks.py ← Dokument-Retrieval-Regeln
├── plan_checks.py ← Deterministische Plan-Qualitaetsregeln
├── approval_checks.py ← Approval-/Bestaetigungsregeln
├── policy_checks.py ← Security-/Anti-Pattern-Regeln aus CSV
├── rule_loader.py ← CSV-Loader + kleiner Reload-Cache
├── llm_check.py   ← LLM-basierte Plan-Prüfung
└── prompts.py     ← Prompt-Aufbau
```

---

## Dateien

### `verifier.py`
Einstiegspunkt. Ruft zuerst `safety.py` auf — bei Hard Block sofort zurück.
Danach `llm_check.py` für die inhaltliche Plan-Prüfung.
Reicht `user_text` und optional `document_context` an `input_prepare.py`
weiter, damit Long-Document-Inputs nicht wie normaler Kurztext vorbereitet
werden.
Enthält **keine eigene Logik** — nur Verdrahtung.
**Max 80 Zeilen.**

### `input_prepare.py`
Bereitet den Verify-Input für den späteren Control-/LLM-Check vor.
Trennt:

- normalen Chat-Input
- Long-Document-Input mit `document_summary` und Dokument-Metadaten

Aktueller Zweck:

- `CONTROL_PROMPT_USER_CHARS` nicht mehr implizit nur auf Rohtext anwenden
- für Long-Document schon jetzt einen kontrollierten Summary-/Meta-Block bereitstellen
- fuer Long-Document auch bekannte `workspace_entry_ids`, strukturierte Kandidatenlisten, den aktiven `document_retrieval_mode`, ein kompaktes `question_focus`-Signal und einen verdichteten `retrieval_plan` sichtbar machen
**Max 100 Zeilen.**

### `contracts.py`
Alle Datenstrukturen: `VerifierResult`, `Verdict`.
Importiert **nichts** aus dem eigenen Modul — nur stdlib.
**Max 80 Zeilen.**

`Verdict` ist ein internes Core-Contract. Externe Chat-Events mappen diese Werte
an der Core-/Adapter-Grenze; siehe `docs/contracts/10-chat-event-contract.md`.

```python
class Verdict(Enum):
    APPROVED   = "approved"     # Plan ist gut → weiter zu Output / Task Loop
    REJECTED   = "rejected"     # Plan abgelehnt → zurück zu Thinking mit Hint
    HARD_BLOCK = "hard_block"   # Sofort blockieren, nicht weiterleiten

@dataclass
class VerifierResult:
    verdict:  Verdict
    hint:     Optional[str]  # Nur bei REJECTED: konkreter Hinweis für Thinking
    warnings: List[str]      # Soft-Warnings bei APPROVED
    reason:   str            # Warum diese Entscheidung
```

### `safety.py`
Deterministischer Sicherheits-Check — **kein LLM-Call**.
Verdrahtet nur noch drei getrennte Check-Klassen:

- `document_checks.py` fuer Long-Document-Retrieval-Regeln
- `plan_checks.py` fuer operative Vorbedingungen und Mutationsregeln
- `approval_checks.py` fuer explizite Approval-/Bestaetigungspfade
- `policy_checks.py` fuer Security-/Anti-Pattern-Matches aus CSV

Damit bleiben Laden, Matching und fachliche Regelgruppen getrennt und
`safety.py` selbst enthaelt keine Hardcode-Patternlisten mehr.
**Max 150 Zeilen.**

### `document_checks.py`
Deterministische Dokument-Retrieval-Regeln — **kein LLM-Call**.
Prueft fuer Long-Document-Inputs, ob dokumentbezogene `workspace_get`-Schritte
zum bekannten Dokumentkontext und zu vorhandenen Suchschritten passen. Nutzt
den kompakten `retrieval_plan`, um widerspruechliche Modi wie
`structure_first`, `semantic_first`, `workspace_first` und `workspace_only`
frueh deterministisch abzuweisen.
**Max 150 Zeilen.**

### `plan_checks.py`
Deterministische Plan-Qualitaetsregeln — **kein LLM-Call**.
Wertet CSV-Regeln aus `verifier_plan_rules.csv` aus und prueft derzeit u.a.:

- `deploy_container` nur nach Blueprint-Kontext
- riskantes `exec_in_container` nur nach Container-Kontext
- `stop_container`, `blueprint_update/delete` nur nach passendem Read-/Inspect-Kontext
- exakte Dokument-Lookups mit `memory_semantic_search` nur zusammen mit `workspace_get`
- `workspace_update/delete`, `conversation_meta_upsert`, `secret_delete` nur nach Zielkontext
- riskante operative Schritte nicht als erster echter Tool-Schritt

Verstoesse fuehren zu `REJECTED` mit regelgetriebenem `hint`.
**Max 150 Zeilen.**

### `approval_checks.py`
Deterministische Approval-Regeln — **kein LLM-Call**.
Wertet `verifier_approval_rules.csv` aus und prueft derzeit, ob riskante
`needs_confirmation`-Schritte bereits einen expliziten `approval_request` im
Plan haben. Abgedeckt sind aktuell:

- `deploy_container`
- `exec_in_container`
- `blueprint_delete`
- `secret_delete`

Fehlt der Approval-Pfad, fuehrt das zu `REJECTED` mit regelgetriebenem `hint`.
**Max 100 Zeilen.**

### `policy_checks.py`
Deterministische Policy-Regeln — **kein LLM-Call**.
Wertet `security_policies.csv` und `procedural_rag/anti_patterns.csv` aus.
Harte Security-Treffer fuehren je nach Regel zu `HARD_BLOCK` oder `REJECTED`;
kausale Anti-Pattern-Treffer fuehren zu `REJECTED` mit Korrekturhinweis aus der
CSV.
**Max 150 Zeilen.**

### `rule_loader.py`
Kleiner CSV-Loader fuer den Verifier.
Liest `security_policies.csv`, `anti_patterns.csv` und
`verifier_plan_rules.csv` sowie `verifier_approval_rules.csv` ueber einen
einfachen mtime-basierten Cache ein, damit Regeldateien hot-reload-faehig
bleiben ohne dass Fachlogik in den Loader wandert.
**Max 100 Zeilen.**

### `llm_check.py`
Einziger LLM-Call im gesamten Verifier-Modul.
Prüft ob der Plan inhaltlich sinnvoll ist und zur Anfrage passt.
Gibt `APPROVED`, `REJECTED + Hint` oder `HARD_BLOCK` zurück.
Wird nur aufgerufen wenn `safety.py` keinen Hard Block meldet.
Ist per `CONTROL_LLM_CHECK_ENABLE` kontrolliert schaltbar und faellt bei
deaktiviertem Flag oder Fehlern offen auf `APPROVED` zurueck. Fuer den
Dokumentpfad kann der Check jetzt separat ueber
`CONTROL_LLM_CHECK_LONG_DOCUMENT_ENABLE` aktiviert werden, ohne normale Inputs
global mitzuschalten. Fuer den kontrollierten Rollout kann derselbe Check jetzt
auch ueber `CONTROL_LLM_CHECK_MODES` feiner eingeschraenkt werden:

- `off`
- `long_document`
- `task_loop`
- `needs_confirmation`
- `all`

Mehrere Modi koennen komma-separiert kombiniert werden, z.B.
`CONTROL_LLM_CHECK_MODES=long_document,needs_confirmation`.
Long-Document-Inputs nutzen dabei den bestehenden `deep`-Pfad fuer Timeout und
Endpoint-Override. Widerspruechliche APPROVED-Warnings werden dabei schmal nach
`question_focus` nachbearbeitet, ohne das Verdict selbst umzuschreiben.
Ungueltige, unvollstaendige oder widerspruechliche JSON-Entscheidungen des
Modells werden jetzt als `REJECTED` behandelt; nur technische Call-Fehler
bleiben fail-open.
Fuer lokalen Ollama nutzt der Check `CONTROL_ENDPOINT`, falls gesetzt,
sonst `OLLAMA_BASE`.
**Max 150 Zeilen.**

### `prompts.py`
Baut den Verifikations-Prompt aus `intelligence_modules` zusammen.
Nutzt die Layer-Prompts `control`, `control_verify_input` und
`control_verify_plan`. Reicht fuer Long-Document-Inputs jetzt auch kompakte
Retrieval-Signale in den `VERIFY-INPUT`, damit der optionale LLM-Check
dokumentbezogene Leseplaene besser einordnen kann. Die eigentliche
retrieval-mode-spezifische Steuerung liegt weiter in den Markdown-Layern, nicht
im Python-Code. Kein Prompt-Text liegt im Python-Code.
**Max 100 Zeilen.**

---

## Regeln

- **Max 200 Zeilen pro Datei** — wird eine Datei größer, wird sie aufgeteilt
- **`safety.py` macht keinen LLM-Call** — nur Verdrahtung der deterministischen Checks
- **Nur ein LLM-Call im gesamten Modul** — in `llm_check.py`
- **Kein Tool-Routing** — der Verifier entscheidet nicht welche Tools genutzt werden
- **Keine execution_mode / turn_mode Derivation** — Thinking macht das selbst
- **Hard Block vor LLM-Call** — wenn `safety.py` blockt, wird `llm_check.py` nicht aufgerufen
- **Kein Regelwerk hardcodiert** — Security-, Anti-Pattern- und Plan-Regeln kommen aus `intelligence_modules`
- **`contracts.py` ist das Fundament** — wird zuerst geschrieben, danach nichts mehr daran ändern ohne Review

---

## Entscheidungsfluss

```
ThinkingPlan eingehend
        ↓
[ safety.py ]  ← deterministisch, kein LLM
    ├── document_checks.py
    ├── plan_checks.py
    ├── approval_checks.py
    └── policy_checks.py
    HARD_BLOCK → sofort zurück, kein LLM-Call
        ↓ (wenn safe)
[ llm_check.py ]  ← ein LLM-Call
    APPROVED   → weiter zu Output / Task Loop
    REJECTED   → zurück zu Thinking mit Hint
    HARD_BLOCK → sofort zurück
```

---

## Output

```python
# Plan OK
VerifierResult(verdict=Verdict.APPROVED, hint=None, warnings=[], reason="Plan valide")

# Plan abgelehnt — Thinking bekommt den Hint für Re-Planning
VerifierResult(verdict=Verdict.REJECTED, hint="Schritt 2 fehlt Blueprint-Validierung vor Deploy", warnings=[], reason="Unvollständiger Plan")

# Hard Block — wird nicht weitergeleitet
VerifierResult(verdict=Verdict.HARD_BLOCK, hint=None, warnings=[], reason="Malicious intent detected")
```

---

## Abhängigkeiten

```
verifier.py
  ├── safety.py
  │     ├── document_checks.py
  │     ├── plan_checks.py
  │     ├── approval_checks.py
  │     ├── policy_checks.py
  │     └── contracts.py
  └── llm_check.py
        ├── contracts.py
        ├── prompts.py
        └── core/llm_provider_client.py

intelligence_modules (nur lesend):
  ├── prompts/layers/control*.md
  ├── cim_skill_rag/security_policies.csv
  ├── cim_skill_rag/verifier_plan_rules.csv
  ├── cim_skill_rag/verifier_approval_rules.csv
  └── procedural_rag/anti_patterns.csv
```

---

## Was der Verifier NICHT macht

- Kein Tool-Routing
- Keine execution_mode oder turn_mode Derivation
- Keine CIM-Policy-Ausführung (das macht der Classifier)
- Kein Kontext-Aufbau
- Kein Re-Planning (das macht Thinking)

---

## Nächster Schritt

- Status und offene Feinarbeit fuer den Dokumentpfad: siehe [[16-long-input-document-routing|Long Input & Document Routing]]
- naechster operative Rollout-Schritt: `CONTROL_LLM_CHECK_MODES=long_document` zuerst in realen Faellen erproben, danach `needs_confirmation` oder `task_loop`, und `all` erst nach stabiler Feldbeobachtung
