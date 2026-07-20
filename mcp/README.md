# MCP — Model Context Protocol Layer

Zentrale Schnittstelle zwischen der TRION-Pipeline und allen Tool-Servern.
Neue Fähigkeiten werden durch Hinzufügen eines neuen MCP-Servers erschlossen — die Pipeline muss nichts davon wissen.

**Einzige Aufgabe:** Tool-Calls routen, Transport abstrahieren, Tool-Wissen im Memory registrieren.

---

## Modulstruktur

```
mcp/
├── hub.py                ← Zentraler Router
├── registry.py           ← Tool-Registrierung im Knowledge Graph
├── client.py             ← High-level Hilfsfunktionen
├── config.py             ← MCP-Server-Konfiguration laden
├── endpoint.py           ← FastAPI-Endpunkte für WebUI
├── installer.py          ← Router-Wiring für Installer-Endpunkte
├── installer_common.py   ← gemeinsame Installer-Helfer
├── installer_install_routes.py ← Upload-/Install-Flow
├── installer_manage_routes.py  ← List/Toggle/Delete/Config
└── transports/
    ├── http.py           ← HTTP Transport
    ├── sse.py            ← SSE Transport
    └── stdio.py          ← STDIO Transport
```

---

## Dateien

### `hub.py`
Zentraler Singleton-Router. Baut Verbindungen zu allen aktivierten MCP-Servern auf,
entdeckt deren Tools und routet `call_tool()` automatisch zum richtigen Server.
Transport-Typ (HTTP/SSE/STDIO) wird pro Server aus der Config bestimmt.
**Kein Business-Logic — nur Routing.**
**Max 150 Zeilen.**

### `registry.py`
Registriert alle entdeckten Tools einmalig beim Start im sql-memory Knowledge Graph.
Nutzt einen Versions-Hash — Re-Registrierung nur wenn sich Tools geändert haben.
Stellt `detection_rules()` für den Control-Classifier bereit.
Stellt `get_system_knowledge()` für den Orchestrator bereit.
**Max 150 Zeilen.**

### `client.py`
High-level Hilfsfunktionen die von der Pipeline genutzt werden.
- `call_tool()` — einheitlicher Wrapper über den Hub
- `autosave_assistant()` — Antwort ins Memory speichern
- `get_fact()` — strukturierten Fakt laden
- `search_memory()` — Textsuche als Fallback
- `semantic_search()` — Embedding-basierte Suche
- `graph_search()` — Graph-Walk für verbundene Informationen
**Max 200 Zeilen.**

### `config.py`
Lädt die MCP-Server-Registry aus `mcp_registry.json`.
Stellt `get_enabled_mcps()`, `get_all_mcps()`, `get_mcp_config()` bereit.
Kein hardcodierter Server-Config im Code.
**Max 50 Zeilen.**

### `endpoint.py`
FastAPI-Endpunkte für die WebUI:
- `GET /mcp` — Hub-Status
- `GET /mcp/status` — Online-Status aller Server
- `GET /mcp/tools` — Alle verfügbaren Tools
**Max 100 Zeilen.**

### `installer.py`
Installer-Einstiegspunkt. Haengt Install- und Management-Router ein.
**Max 50 Zeilen.**

### `installer_common.py`
Gemeinsame Konstanten und Helper fuer den Installer:
Custom-MCP-Pfad, Core-MCP-Schutz, Health-Check, Config-Lesen/Schreiben.
**Max 150 Zeilen.**

### `installer_install_routes.py`
Upload-/Install-Flow fuer lokale ZIP-Bundles.
Schreibt in `mcp_registry.json` und triggert danach einen echten Hub-Reload.
**Max 200 Zeilen.**

### `installer_manage_routes.py`
List, Details, Toggle, Delete und Config-Update fuer installierte MCPs.
**Max 200 Zeilen.**

### `transports/`
Drei Implementierungen für verschiedene Kommunikationsprotokolle.
Jede Datei: **Max 150 Zeilen.**

---

## Regeln

- **Max 200 Zeilen pro Datei**
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
3. Hub neu laden oder per Installer synchronisieren → Tools werden automatisch entdeckt und registriert

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
