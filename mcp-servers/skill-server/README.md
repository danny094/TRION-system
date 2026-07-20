# Skill Server — MCP Server

Installiert, verwaltet und führt Skills aus.
Skills sind isolierte Python-Funktionen die TRION neue Fähigkeiten geben.

---

## Modulstruktur

```
mcp-servers/skill-server/
├── server.py          ← MCP-Einstiegspunkt, registriert alle Tools
├── skill_manager.py   ← Skill CRUD + Ausführung
├── skill_knowledge.py ← Wissensbasis (Kategorien, Suche)
├── skill_memory.py    ← Skill-Persistenz im Memory
├── skill_cim_light.py ← Leichte Sicherheitsprüfung für Skill-Code
├── mini_control_core.py ← Vollständige Code-Sicherheitsanalyse
├── secret_scanner.py  ← Erkennt Secrets/Credentials im Code
├── cim_rag.py         ← RAG-Suche über CIM-Daten
└── data/              ← CSV-Dateien (Patterns, Templates, Policies)
```

---

## Registrierte MCP-Tools

| Tool | Beschreibung |
|------|--------------|
| `list_skills` | Alle installierten Skills auflisten |
| `get_skill_info` | Details zu einem Skill |
| `install_skill` | Neuen Skill installieren |
| `uninstall_skill` | Skill deinstallieren |
| `run_skill` | Skill ausführen |
| `search_skill_knowledge` | Semantische Suche in der Wissensbasis |
| `get_skill_categories` | Verfügbare Kategorien |
| `validate_skill_code` | Code vor Installation prüfen |

---

## Regeln

- **server.py ist der einzige Einstiegspunkt** — kein direkter Import von außen
- **Kein Import aus `core/`** — vollständig isoliert
- **Skill-Code läuft in einem Sandbox-Prozess** — kein direkter `exec()` im Server
- **`validate_skill_code` vor jeder Installation** — Security-Gate ist nicht optional

---

## Bekannte Aufräum-Aufgaben

- [ ] `mini_control_core.py` (1815 Zeilen) aufteilen in `analyzer.py` + `policy.py`
- [ ] `skill_manager.py` (910 Zeilen) aufteilen in `manager.py` + `executor.py`
- [ ] Von FastAPI → FastMCP migrieren (server.py war noch FastAPI)

---

## Konfiguration

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `SKILLS_DIR` | `/skills` | Verzeichnis für installierte Skills |
| `EXECUTOR_URL` | `http://tool-executor:8000` | Tool Executor für sandboxed Ausführung |
| `SKILL_PACKAGE_INSTALL_MODE` | `allowlist_auto` | Paket-Installationspolitik |

---

## In mcp_registry.json eintragen

```json
"skill-server": {
  "enabled": true,
  "transport": "http",
  "url": "http://trion-skill-server:8088/mcp",
  "description": "Skill-Verwaltung und Ausführung"
}
```
