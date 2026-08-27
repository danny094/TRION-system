# MCP — Model Context Protocol Layer

Zentrale Schnittstelle zwischen der TRION-Pipeline und allen Tool-Servern.
Neue Fähigkeiten werden durch Hinzufügen eines neuen MCP-Servers erschlossen — die Pipeline muss nichts davon wissen.

**Einzige Aufgabe:** Tool-Calls routen, Transport abstrahieren, Tool-Wissen im Memory registrieren.

---

## Modulstruktur

```
mcp/
├── Routing / Hub
│   ├── hub.py             ← Zentraler Router (Catalog-Snapshot-Consumer)
│   ├── hub_listing.py     ← Admin-Projektion für list_mcps()
│   ├── catalog_dispatch.py ← Call-Dispatch über ein acquired Route-Token
│   ├── client.py          ← High-level Hilfsfunktionen
│   ├── registry.py        ← Tool-Registrierung im Knowledge Graph
│   └── endpoint.py        ← FastAPI-Endpunkte für WebUI
├── Desired-State
│   ├── config.py          ← Desired-State-Producer + Legacy-Projektionen
│   └── desired_state.py   ← typisierte Source-/Desired-State-Komposition
├── Catalog-Lifecycle
│   ├── catalog_contracts.py   ← immutable Contracts (Snapshot, Tokens, Status)
│   ├── transport_instances.py ← Desired-Eintrag → Transportinstanz binden
│   ├── catalog_discovery.py   ← P13-tools/list-Outcomes je Desired-ID
│   ├── catalog_builder.py     ← Catalog-Candidate komponieren
│   └── catalog_lifecycle.py   ← Publish/Cutover, Acquire, Revoke/Retire
├── Protocol & Tool Results (P13-owned)
│   ├── protocol_negotiation_contracts.py ← Version 2024-11-05 + Negotiation
│   ├── protocol_contracts.py  ← Transport-/tools-list-Protocol-Contracts
│   ├── protocol_tools_list.py ← typisiertes tools/list-Result
│   ├── tool_result_contracts.py ← kanonisches MCPToolResultEnvelope
│   ├── structural_validation_contracts.py ← typisiertes Strukturresultat
│   └── structural_validator.py ← einziger generischer Strukturvalidator
├── Installer
│   ├── installer.py            ← Router-Wiring für Installer-Endpunkte
│   ├── installer_common.py     ← gemeinsame Installer-Helfer
│   ├── installer_install_routes.py ← Upload-/Install-Flow
│   ├── installer_manage_routes.py  ← List/Toggle/Delete/Config
│   ├── installer_confirmation.py   ← typisierte Registry-Reload-Postcondition
│   └── installer_health.py         ← Post-Install-Health-Projektion
└── transports/
    ├── http.py           ← HTTP Transport
    ├── sse.py            ← SSE Transport
    └── stdio.py          ← STDIO Transport
```

> Weitere Installer-Split-Module (`installer_manifest*.py`, `installer_reconcile.py`,
> `installer_registry*.py`, `installer_runtime.py`, `installer_paths.py`,
> `installer_receipt.py`, `installer_tool_intents.py`, `installer_manage_config.py`)
> liegen real im Paket; führend bleibt [[21-mcp-installer|MCP-Installer]].

---

## Dateien

### `hub.py`
Zentraler Singleton-Router. `initialize()` baut per `catalog_builder.build_catalog_snapshot()`
einen immutable Catalog-Snapshot und publiziert ihn über `catalog_lifecycle.publish_catalog()`.
`list_tools()` und `get_mcp_for_tool()` lesen ausschließlich `catalog_lifecycle.current_catalog_snapshot()`;
`call_tool()` erwirbt ein Route-Token über `catalog_lifecycle.acquire_route()` und dispatcht darüber.
Die Tool-/Route-Sicht stammt also aus dem publizierten Snapshot, nicht aus Live-Discovery pro Aufruf.
Transport-Typ (HTTP/SSE/STDIO) wird pro Server aus dem Desired State gebunden.
**Kein Business-Logic — nur Routing.**

### `registry.py`
Registriert die Tools des publizierten Catalog-Snapshots im sql-memory Knowledge Graph
(`register_all()` liest den Snapshot, keine eigene Live-Discovery).
Nutzt einen Versions-Hash — Re-Registrierung nur wenn sich Tools geändert haben.
Stellt `detection_rules()` für den Control-Classifier bereit.
Stellt `get_system_knowledge()` für den Orchestrator bereit.

### `client.py`
High-level Hilfsfunktionen die von der Pipeline genutzt werden.
- `call_tool()` — einheitlicher Wrapper über den Hub
- `autosave_assistant()` — Antwort ins Memory speichern
- `get_fact()` — strukturierten Fakt laden
- `search_memory()` — Textsuche als Fallback
- `semantic_search()` — Embedding-basierte Suche
- `graph_search()` — Graph-Walk für verbundene Informationen

### `config.py`
Lädt die MCP-Server-Registry aus `mcp_registry.json`.
Autoritativer typisierter Producer ist `get_mcp_desired_state()` (immutable `MCPDesiredState`,
komponiert über `desired_state.py`). `get_all_mcps()`, `get_enabled_mcps()` und `get_mcp_config()`
sind daraus abgeleitete Legacy-Projektionen; `_load_registry()` ist eine reine mutable Legacyprojektion.
Kein hardcodierter Server-Config im Code.

### `desired_state.py`
Typisierte Grenze zwischen roher Registry-Source und komponiertem Desired State.
`load_registry_source()` liefert ein typisiertes Source-Outcome, `compose_mcp_desired_state()`
validiert und trennt Core-Defaults von reiner Custom-Registry (fail-closed bei ID-Kollision).

### `catalog_contracts.py` / `catalog_builder.py` / `catalog_discovery.py` / `transport_instances.py` / `catalog_lifecycle.py`
Die P14-Catalog-Schicht. `transport_instances.bind_transport_instance()` bindet je Desired-ID
genau eine Transportinstanz; `catalog_discovery.discover_catalog_outcomes()` bildet daraus
je ID genau ein Discovery-Outcome (nur `BOUND` ruft ein P13-`tools/list` auf);
`catalog_builder.build_catalog_snapshot()` komponiert einen immutable Catalog-Candidate;
`catalog_lifecycle` publiziert per Cutover (`publish_catalog`), vergibt Route-Tokens (`acquire_route`)
und retirert alte Transporte (`revoke_catalog_routes`). Contracts (Snapshot, Tokens, Status-Enums)
liegen in `catalog_contracts.py`.

### P13 Protocol-, Result- und Structured-Output-Vertrag

`protocol_negotiation_contracts.py` akzeptiert ausschließlich MCP
`2024-11-05` und liefert einen immutable Negotiation-Status:
`NEGOTIATED`, `MISSING`, `MALFORMED` oder `UNSUPPORTED`. Transporte und
Endpoint dürfen Folgearbeit nur nach `NEGOTIATED` ausführen; es gibt keinen
impliziten Default, Fallback oder stilles Versionsupgrade.

`tool_result_contracts.py::MCPToolResultEnvelope` vereinheitlicht STDIO, HTTP
und SSE. Das Envelope bewahrt `content` und `structuredContent` mit
getrennter `MISSING`-/`EMPTY`-/`VALUE`-Presence; `isError` ist
ausschließlich `MISSING` oder `VALUE` und niemals `EMPTY`. Seine einzige
Fehlerautorität ist `MCPToolCallStatus` mit `SUCCESS`, `TOOL_FAILURE`,
`PROTOCOL_FAILURE` und `TRANSPORT_FAILURE`; `isError=true` projiziert auf
`TOOL_FAILURE`, Diagnose- oder Fehlertexte klassifizieren den Status nicht.

Für Schema-v2-Toolintents mit `mcp_output_schema` wird das Live-`outputSchema`
über defensive Kopien im Descriptor-Snapshot und Detailmapping bis
`core/task_loop/tool_execution_contracts.py::TaskToolCall` transportiert;
erst `TaskToolCall` friert das Schema rekursiv immutable ein. Der
`structural_validator.py::validate_structured_output` validiert ein
erfolgreiches Envelope genau einmal und liefert
`MCPStructuralValidationResult`. `adapters/tool_runner_bridge.py` bewahrt
dieses Resultat getrennt vom `TaskToolResultStatus` bis
`TaskToolResult.structural_result`; fehlendes oder ungültiges Schema ändert
den Ausführungsstatus nicht.

P13 endet an dieser typisierten P12-Grenze. Evidence, Completion, Renderer und
öffentliche Projektion bleiben P12-owned und werden durch Strukturvalidierung
nicht automatisch freigegeben.

### `endpoint.py`
FastAPI-Endpunkte für die WebUI:
- `POST /mcp` — MCP-Protokoll-Handler (Streamable HTTP)
- `GET /mcp/status` — MCPs + Tool-Zahl
- `POST /mcp/refresh` — Reload triggern
- `GET /mcp/tools` — Alle verfügbaren Tools
`online`/`routable` spiegeln den publizierten Catalog-Snapshot: DISABLED-MCPs bleiben
administrativ sichtbar, aber offline und ohne Route.

### `installer.py`
Installer-Einstiegspunkt. Haengt Install- und Management-Router ein.

### `installer_common.py`
Gemeinsame Konstanten und Helper fuer den Installer:
Custom-MCP-Pfad, Core-MCP-Schutz, Health-Check, Config-Lesen/Schreiben.

### `installer_install_routes.py`
Upload-/Install-Flow fuer lokale ZIP-Bundles.
Schreibt in `mcp_registry.json` und triggert danach einen echten Hub-Reload.

### `installer_manage_routes.py`
List, Details, Toggle, Delete und Config-Update fuer installierte MCPs.

### Legacy-Core-Registry-Migration

`mcp/installer_registry.py::migrate_legacy_core_entries` ist der einzige
explizite Operatorpfad fuer historische Custom-Eintraege, deren ID inzwischen
von `mcp/config.py::core_mcp_names()` als Core-MCP geliefert wird. Der normale
Reader bleibt bei solchen Kollisionen fail-closed; Start, Registry-Lesen und
Catalog-Aufbau migrieren niemals automatisch.

Der Einstiegspunkt `scripts/migrate_mcp_registry_core_entries.py` ist ohne
Option ein side-effect-freier Dry-run. Nur `--apply` erstellt zuerst ein
byteidentisches, mit dem vollstaendigen SHA-256 der Ursprungsbytes gebundenes
Backup neben der Registry und ersetzt danach die reine Custom-Registry ueber
den atomaren Byte-Writer. Ein Registry-spezifischer kooperativer OS-Lock
serialisiert alle projektseitigen Installer- und Migrationswriter
prozessuebergreifend; zusaetzliche Bytevergleiche brechen erkannte stale States
ohne Retry ab. Manuelle oder externe Writer ausserhalb dieses Locks gehoeren
nicht zum unterstuetzten Schreibvertrag. Duplicate JSON Keys werden nur an
dieser Operatorgrenze fail-closed abgelehnt. Nicht als Core gefuehrte
Custom-Eintraege bleiben unveraendert erhalten.

### `transports/`
Drei Implementierungen für verschiedene Kommunikationsprotokolle.

---

## Regeln

- **Zeilen-Cap pro Datei: siehe docs/governance/07-design-rules.md**
- **hub.py kennt keine Pipeline-Module** — kein Import aus `core/`
- **registry.py ist best-effort** — Fehler beim Registrieren stoppen nicht den Start
- **client.py hat keinen FastAPI-Router** — nur reine Funktionen
- **Neue Fähigkeit = neuer MCP-Server** — nicht neuer Code in hub.py

---

## Wie es in die Pipeline passt

```
core/task_loop/executor.py
        ↓
mcp/client.py → call_tool()
        ↓
mcp/hub.py → routet zum richtigen Server
        ├── memory/   (sql-memory MCP)
        ├── skills/   (skill-server MCP)
        ├── system/   (system-addons MCP)
        └── [beliebig erweiterbar via mcp_registry.json]

core/orchestrator/context.py
        ↓
mcp/client.py → get_fact() / semantic_search() / graph_search()
        ↓
memory MCP Server
```

---

## Neue Fähigkeit hinzufügen

1. MCP-Server implementieren (FastMCP oder beliebiges MCP-Framework)
2. Eintrag in `mcp_registry.json` hinzufügen:
```json
{
  "mein-server": {
    "enabled": true,
    "transport": "http",
    "url": "http://mein-server:8000/mcp",
    "description": "Was dieser Server kann"
  }
}
```
3. Hub neu laden oder per Installer synchronisieren → der Reload baut einen vollständigen
   Catalog-Candidate, publiziert ihn per Cutover und retirert die alten Transporte; die neuen
   Tools erscheinen danach aus dem publizierten Snapshot

**Kein Code-Änderung in hub.py, registry.py oder client.py nötig.**

---

## Konfiguration

`mcp_registry.json` im TRION-Root (Pfad über `MCP_REGISTRY_PATH` überschreibbar):

```json
{
  "sql-memory": {
    "enabled": true,
    "transport": "http",
    "url": "http://trion-memory:8001/mcp",
    "description": "Persistentes Memory mit Semantic Search und Graph"
  },
  "skill-server": {
    "enabled": false,
    "transport": "http",
    "url": "http://trion-skills:8002/mcp",
    "description": "Skill-Verwaltung und Ausführung"
  }
}
```

---

## Was MCP NICHT macht

- Keine Business-Logic
- Kein direkter LLM-Call
- Keine Pipeline-Entscheidungen
- Keine Authentifizierung der User-Requests (das macht die Admin-API)
