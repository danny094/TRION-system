# SQL Memory — MCP Server

Persistenter Speicher für Memory, Fakten, Secrets, Workspace, Graph und Conversation-Metadaten.
Läuft als eigenständiger Container. TRION importiert dieses Modul **niemals direkt** — alles läuft über Tool-Calls durch den MCP Hub.

---

## Modulstruktur

```
memory/
├── embedding.py              ← Embedding-Client (Ollama) — inlined, kein Import aus utils/
├── vector_store.py           ← Cosine-Similarity-Suche auf SQLite-Embeddings-Tabelle
├── graph/
│   ├── graph_builder.py      ← Node- und Edge-Konstruktion
│   └── graph_store.py        ← Graph-CRUD auf SQLite
└── memory_mcp/
    ├── server.py             ← Einstiegspunkt — nur Verdrahtung, keine Logik
    ├── config.py             ← DB_PATH + Layer-Klassifikations-Keywords
    ├── database.py           ← Re-Exporter aus db/ (Rückwärts-Kompatibilität)
    ├── tools.py              ← register_tools() ruft alle Tool-Gruppen auf
    ├── db/                   ← DB-Logik nach Domain aufgeteilt (je max. 200 Zeilen)
    │   ├── schema.py         ← init_db() + migrate_db()
    │   ├── memory.py         ← Memory-Tabelle + FTS-Repair
    │   ├── facts.py          ← Fakten-CRUD
    │   ├── skill_metrics.py  ← Skill-Metriken-CRUD
    │   ├── workspace.py      ← Workspace-Entries-CRUD
    │   ├── conversation_meta.py ← ConversationMeta-CRUD + Write-Policy
    │   ├── secrets.py        ← Secrets-Encryption + CRUD
    │   ├── secrets_table.py  ← Secrets-Tabellen-Schema
    │   ├── artifacts.py      ← Artifact-Registry-CRUD
    │   ├── task_tables.py    ← Task/Embedding-Tabellen-Schema
    │   └── __init__.py       ← Re-Exporter aller öffentlichen Funktionen
    └── tool_groups/          ← Tool-Registrierungen nach Domain aufgeteilt
        ├── memory_tools.py
        ├── memory_admin_tools.py
        ├── embedding_tools.py
        ├── graph_tools.py
        ├── graph_admin_tools.py
        ├── workspace_tools.py
        ├── skill_tools.py
        ├── secret_tools.py
        ├── conversation_meta_tools.py
        └── maintenance_tools.py
```

---

## Registrierte MCP-Tools

### Memory

| Tool | Beschreibung |
|------|--------------|
| `memory_save` | Freien Text speichern |
| `memory_recent` | Neueste Einträge abrufen |
| `memory_search` | Text-Suche (SQL LIKE) |
| `memory_search_fts` | Volltext-Suche via FTS5 |
| `memory_search_layered` | Schichtweise Suche (stm → mtm → ltm) |
| `memory_fact_save` | Strukturierten Fakt speichern |
| `memory_fact_load` | Fakt abrufen |
| `memory_autosave` | Autosave-Hook für User-Nachrichten |

### Memory Admin

| Tool | Beschreibung |
|------|--------------|
| `memory_delete` | Einzelnen Eintrag löschen |
| `memory_delete_bulk` | Mehrere Einträge löschen |
| `memory_reset` | Alle Memory-Einträge zurücksetzen |
| `memory_all_recent` | Alle neuesten Einträge über Layer hinweg |

### Embedding / Semantische Suche

| Tool | Beschreibung |
|------|--------------|
| `memory_semantic_save` | Eintrag mit Embedding speichern |
| `tool_embedding_save` | Tool-Definition mit Embedding speichern |
| `memory_semantic_search` | Semantische Ähnlichkeitssuche |
| `memory_embedding_versions` | Aktive/stale Embedding-Versionen |
| `memory_embedding_rebatch` | Re-embedding für veraltete Einträge |

### Graph

| Tool | Beschreibung |
|------|--------------|
| `memory_graph_search` | Graph-Walk — verbundene Informationen finden |
| `memory_graph_neighbors` | Nachbarn eines Graph-Nodes |
| `memory_graph_stats` | Graph-Statistiken |
| `memory_graph_save` | Node im Graph + VectorStore speichern |
| `graph_add_node` | Graph-Node mit Embedding anlegen |

### Graph Admin

| Tool | Beschreibung |
|------|--------------|
| `graph_find_duplicate_nodes` | Doppelte Nodes finden |
| `graph_merge_nodes` | Nodes zusammenführen |
| `graph_prune_orphans` | Verwaiste Nodes entfernen |

### Workspace

| Tool | Beschreibung |
|------|--------------|
| `workspace_save` | Workspace-Eintrag speichern |
| `workspace_list` | Einträge auflisten, optional gefiltert |
| `workspace_get` | Einzelnen Eintrag abrufen |
| `workspace_update` | Eintrag aktualisieren |
| `workspace_delete` | Eintrag löschen |

### Secrets

| Tool | Beschreibung |
|------|--------------|
| `secret_save` | Verschlüsseltes Secret speichern oder aktualisieren |
| `secret_get` | Entschlüsselten Secret-Wert abrufen (nur intern) |
| `secret_list` | Alle Secret-Namen auflisten (Werte nie zurückgegeben) |
| `secret_delete` | Secret per Name löschen |

### Conversation Meta

| Tool | Beschreibung |
|------|--------------|
| `conversation_meta_get` | Persistierte Conversation-Metadaten abrufen |
| `conversation_meta_upsert` | Conversation-Metadaten erstellen oder aktualisieren |
| `conversation_write_policy_check` | Prüfen ob Langzeitspeichern erlaubt ist |

### Skill Metrics

| Tool | Beschreibung |
|------|--------------|
| `skill_metric_save` | Skill-Metrik speichern |
| `skill_metric_get` | Skill-Metrik abrufen |
| `skill_metric_list` | Alle Skill-Metriken auflisten |

### Maintenance

| Tool | Beschreibung |
|------|--------------|
| `maintenance_run` | KI-gestützte Wartungsaufgabe — Memory organisieren und bereinigen |
| `memory_healthcheck` | Server-Liveness prüfen |

---

## Konfiguration

| ENV-Variable | Default | Beschreibung |
|---|---|---|
| `DB_PATH` | `/app/data/memory.db` | SQLite-Datenbankpfad |
| `OLLAMA_URL` | `http://ollama:11434` | Embedding-Service |
| `EMBEDDING_MODEL` | `hellord/mxbai-embed-large-v1:f16` | Embedding-Modell |
| `SETTINGS_API_URL` | — | Optionaler Settings-API-Endpunkt für Modell-Auflösung |
| `ADMIN_API_URL` | `http://trion-admin-api:8200` | Fallback für Settings-API-URL |
| `SECRET_MASTER_KEY` | `trion-default-secret-key-change-me` | Verschlüsselungs-Master-Key — in Produktion immer setzen |
| `MEMORY_RETRIEVAL_FILTER_ENABLE` | `false` | Retrieval-Policy-Filter aktivieren (`conversation_only`/`disabled` werden durchgesetzt) |
| `SETTINGS_CACHE_TTL` | `60` | Cache-TTL für Settings in Sekunden |

---

## Import-Regel

`memory/` läuft als eigenständiger Container und importiert **nichts** aus `core/`, `utils/`, `mcp/` oder `adapters/`.

`embedding.py` ist bewusst inline dupliziert statt aus `utils/` importiert — der Container hat keinen Zugriff auf das Haupt-Repo.

---

## Start

```bash
python -m memory_mcp.server
```

Im Docker-Stack läuft der Server auf Port `8081`, Pfad `/mcp`.

```bash
docker compose up mcp-sql-memory
```
