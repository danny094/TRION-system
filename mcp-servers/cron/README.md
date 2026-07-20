# Cron Server — MCP Server

Verwaltet autonome Cron-Jobs die TRION-Objectives zeitgesteuert ausführen.
Läuft als eigenständiger Container. TRION importiert diesen Server **niemals direkt** — alles läuft über Tool-Calls durch den MCP Hub.

---

## Modulstruktur

```
mcp-servers/cron/
├── server.py          ← Einstiegspunkt — registriert MCP-Tools, keine Logik
├── contracts.py       ← Exceptions (CronParseError, CronPolicyError) + Policy-Konstanten
├── time_utils.py      ← _utcnow(), _iso(), _parse_iso_datetime()
├── cron_parser.py     ← Cron-Ausdruck parsen, matchen, nächsten Zeitpunkt berechnen
├── hardware.py        ← CPU/RAM lesen, Hardware-Guard bewerten
├── job_builder.py     ← Keyword-Hits, reference_links, job_note_md aufbauen
├── job_normalizer.py  ← normalize_job_payload (standalone)
├── trion_policy.py    ← TRION-Agent-Policy enforcement (standalone)
├── job_policy.py      ← Job + Enqueue-Policy enforcement (standalone)
├── state.py           ← CronJobStore — State, Persistenz, Expression-Cache
├── tick.py            ← tick_loop + tick_once (standalone Coroutinen)
├── dispatch.py        ← dispatch_worker (standalone Coroutine)
├── job_crud.py        ← CronJobCRUDMixin — create/update/delete/pause/resume/run_now
└── scheduler.py       ← AutonomyCronScheduler (thin wiring) + get_scheduler() + validate_cron()
```

---

## Registrierte MCP-Tools

| Tool | Beschreibung |
|------|--------------|
| `cron_list` | Alle konfigurierten Jobs auflisten |
| `cron_get` | Details zu einem Job |
| `cron_create` | Neuen Job erstellen |
| `cron_update` | Job aktualisieren |
| `cron_delete` | Job löschen |
| `cron_pause` | Job pausieren |
| `cron_resume` | Pausierten Job fortsetzen |
| `cron_run_now` | Job sofort ausführen |
| `cron_validate` | Cron-Ausdruck + Objective validieren |
| `cron_status` | Scheduler-Status |
| `cron_queue` | Nächste geplante Ausführungen |

---

## Job-Contract

| Feld | Pflicht | Zweck |
|------|---------|-------|
| `name` | ja | Anzeigename für UI, Listen und Logs |
| `objective` | ja | Ausführbarer Arbeitsprompt für `/api/autonomous/jobs` |
| `conversation_id` | ja | Session-/Kontextanker für Memory und Verlauf |
| `cron` | bei `recurring` | Wiederkehrender Cron-Ausdruck (5-Feld) |
| `run_at` | bei `one_shot` | Einmaliger Ausführungszeitpunkt (ISO 8601) |
| `schedule_mode` | nein | `recurring` (default) oder `one_shot` |
| `max_loops` | nein | Obergrenze für die autonome Task-Loop-Ausführung |
| `created_by` | nein | `user` (default) oder `trion` — steuert Policy-Prüfung |

`objective` ist kein Kurztitel. Der Scheduler dispatcht bei jeder Ausführung diesen Text als Autonomy-Objective. Ohne konkreten Arbeitsprompt hat TRION keinen Arbeitsauftrag.

---

## Regeln

- **`server.py` ist der einzige Einstiegspunkt** — kein direkter Import von außen
- **Kein Import aus `core/`** — vollständig isoliert
- **Objectives werden gegen Policy geprüft** — destruktive Aktionen sind geblockt
- **Jobs dispatchen an die Admin-API** — der Cron-Server führt keine LLM-Calls aus
- **`objective` ist Pflicht** — `name` ersetzt niemals den Arbeitsprompt

---

## Policy

**Erlaubte Objective-Hints:** `status`, `health`, `summary`, `digest`, `report`, `sync`, `cleanup`, `maint`, `monitor`, `backup`, `index`, `archive`, `memory`, `recall`, `plan`, `review`, `check`

**Geblockte Objective-Hints:** `delete`, `drop`, `truncate`, `remove`, `destroy`, `wipe`, `shutdown`, `reboot`, `restart`, `kill`, `secret`, `password`, `token`, `api key`, `credential`, `docker`, `network`, `firewall`, `sudo`, `chmod`, `chown`, `rm -rf`

Context-Approval: `delete` + `cleanup` im selben Objective gilt als unbedenklich. Absolut geblockt bleiben: `rm -rf`, `mkfs`, `dd if=`, `poweroff`.

---

## Konfiguration

| Variable | Standard | Beschreibung |
|---|---|---|
| `CRON_STATE_PATH` | `/app/data/cron_state.json` | JSON-Datei für Job-Persistenz |
| `CRON_TICK_S` | `60` | Scheduler-Tick-Intervall in Sekunden |
| `CRON_MAX_CONCURRENCY` | `3` | Parallele Dispatch-Worker |
| `CRON_PORT` | `8004` | MCP-Server Port |

---

## In mcp_registry.json eintragen

```json
"cron-server": {
  "enabled": true,
  "transport": "http",
  "url": "http://trion-cron-server:8004/mcp",
  "description": "Autonome Cron-Jobs verwalten und ausführen"
}
```
