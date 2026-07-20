---
id: system-tool-surface
title: Tool-Surface im TRION-System
scope: tool_surface
tags:
  - tools
  - endpoints
  - mcp
  - native
  - skills
  - container
priority: 85
retrieval_hints:
  - welche tools
  - tool surface
  - welche endpoints
  - kann ich aufrufen
  - native tools
  - mcp tools
  - verfügbare tools
  - tool liste
confidence: high
last_reviewed: 2026-04-21
---

## Invarianten

- Diese Datei beschreibt Tool-Klassen und typische Domänen, nicht die
  garantierte Live-Toolsurface.
- Konkrete Tool-Existenz kommt nur aus Live-Discovery oder Runtime-Registry.
- MCP-Tools sind dynamisch und dürfen nicht als garantiert angenommen werden.
- Tool-Existenz != Tool-Gesundheit.
- Read-only bevorzugen, bevor write/execute genutzt wird.
- Secrets sind eine sensible Domäne; Secret-Werte sind nicht ausgabefähig.

## Typische Tool-Klassen

### System

| tool_klasse | domäne | modus |
|---|---|---|
| Hardware-/System-Status | system | read_only |

### Skills

| tool_klasse | domäne | modus |
|---|---|---|
| Runtime-Skill-Inventar | skills | read_only |
| Runtime-Skill-Detail | skills | read_only |
| Skill-Erstellung / Persistenz | skills | write |
| Skill-Ausführung | skills | execute |
| Skill-Validierung | skills | read_only |

### Container / Blueprints

| tool_klasse | domäne | modus |
|---|---|---|
| Container-Runtime-Inventar | container | read_only |
| Blueprint-Katalog | blueprints | read_only |
| Container-Anforderung | container | write |
| Container-Ausführung / Command-Run | container | execute |
| Container-Stopp | container | write |
| Container-Logs | container | read_only |
| Container-Ressourcen / Stats | container | read_only |
| Container-Status / Inspektionsdaten | container | read_only |

### Home / Workspace-Dateien

| tool_klasse | domäne | modus |
|---|---|---|
| Home-/Workspace-Lesen | home | read_only |
| Home-/Workspace-Schreiben | home | write |
| Home-/Workspace-Listing | home | read_only |

## MCP- / Dynamic Surface

### Memory / Workspace

| tool_klasse | domäne | modus |
|---|---|---|
| Workspace-Event-Lesen | memory | read_only |
| Workspace-Event-Schreiben | memory | write |
| Memory-Graph-Suche | memory | read_only |

### Secrets

| tool_or_endpoint | domäne | modus |
|---|---|---|
| `GET /api/secrets` | secrets | read_only_names |
| `GET /api/secrets/resolve/{NAME}` | secrets | sensitive_read |
| `secret_save` | secrets | write |

### Skills via MCP / Bridge

| tool_klasse | domäne | modus |
|---|---|---|
| Runtime-Skill-Inventar | skills | read_only |
| Skill-Erstellung / Persistenz | skills | write |
| Skill-Ausführung | skills | execute |

### Weitere dynamische Flächen

| tool_family | quelle | regel |
|---|---|---|
| sequential thinking tools | `sequential-thinking` | dynamisch |
| storage tools | `storage-broker` | dynamisch |
| skill server tools | `trion-skill-server` | dynamisch |
| sql-memory tools | `mcp-sql-memory` | dynamisch |

## Operative Reihenfolge

1. Read-only Tool verwenden, wenn ausreichend.
2. Tool-Klasse mit geringstem Eingriffsgrad bevorzugen, wenn Capability
   gleichwertig ist.
3. MCP-Verfügbarkeit nicht annehmen; discovery/live inventory prüfen.
4. Write-/Execute-Tools nur bei echter Änderungsabsicht.
5. Secret-bezogene Pfade nie für normale Antwortgenerierung verwenden.

## Domänenregeln

### System
- Ein live verfügbares Hardware-/System-Tool liefert Realitätssignale.
- System-Tools ersetzen keine Datenpersistenz.

### Skills
- Runtime-Skill-Inventar-Tools dienen dem Inventar.
- Skill-Detail-Tools dienen der Detailprüfung.
- Skill-Erstellungs-Tools verändern die Systemoberfläche.
- Skill-Ausführungs-Tools führen Operation aus, nicht nur Analyse.

### Container
- Container-Tools greifen in Laufzeitumgebung ein oder lesen sie aus.
- Anforderungs-, Stopp- und Ausführungs-Tools sind verändernd/operativ.

### Secrets
- `GET /api/secrets` gibt nur Namen zurück.
- `GET /api/secrets/resolve/{NAME}` ist sensitiv.
- Secret-Werte dürfen nicht im Tool-Output erscheinen.

## Zugriff

- Für Bestandsaufnahme: read-only Tools zuerst.
- Für Erweiterung: passende Skill-Erstellungs- und Validierungs-Tools.
- Für operative Ausführung: passende Skill- oder Container-Tools.
- Für Secrets: nur Inventar listen oder intern gekapselt verwenden.

## Grenzen

- Diese Datei sagt nicht, welche MCP-Tools aktuell registriert sind.
- Diese Datei sagt nicht, ob ein Tool aktuell gesund ist.
- Diese Datei sagt nicht, welche Ergebnisse ein Tool aktuell liefern wird.
- Diese Datei ersetzt keine Live-Discovery.
