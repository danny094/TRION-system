# TRION Adapters — API Endpoints

Zwei Services: **WebUI** (Frontend + Chat-Proxy) und **Admin-API** (Backend-Logik).

## Lokale Sicherheitsgrenze

- WebUI und direkter Admin-Port binden nur an `127.0.0.1`; der
  Memory-Dienst besitzt keinen Hostport.
- Vor dem ersten Start erzeugt
  `docker compose --profile bootstrap run --rm trion-security-bootstrap`
  das lokale Admin-Credential und die installationsspezifischen Secret-Dateien.
- Browseraufrufe verwenden ein signiertes `HttpOnly`-/`SameSite=Strict`-
  Session-Cookie. Mutierende Methoden brauchen zusaetzlich erlaubte Origin
  und den sessiongebundenen Header `x-csrf-token`.
- Der Secret-Resolve-Token gilt nur fuer
  `GET /api/secrets/resolve/{name}`. Der getrennte Memory-Read-Token gilt nur
  fuer die drei Settings-/Routing-GETs; beide werden aus Secret-Dateien gelesen.
- Docker-Netz-Naehe erzeugt keinen Principal. Die Admin-Middleware prueft
  Browser- und interne Caller vor den Routern.

---

## WebUI

Frontend- und Proxy-Layer zwischen Browser und Admin API. Der fuehrende
kuratierte Vertrag steht in `docs/adapters/17-webui-api-endpoints.md`; die
mechanisch generierte lokale Decorator-Inventar steht in
`docs/reference/20-backend-api-reference.md`. Aus anderen Paketen importierte
und in `main.py` montierte Router bleiben zusaetzlich an ihren Mount- und
Quelldateien gebunden.

### Port 3000
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/` | SPA-Einstieg |
| GET | `/assets/*` | Gebaute Frontend-Assets |
| GET | `/health` | Health-Check |
| GET/POST/... | `/api/*` | Proxy zur Admin API |

Die folgenden Abschnitte katalogisieren Backendpfade der Admin API, nicht
zusaetzliche WebUI-Routen auf Port 3000.

### Maintenance — `/api/maintenance`
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/maintenance/status` | Wartungsstatus abfragen |
| POST | `/api/maintenance/start` | Wartungsmodus starten |

### Personas — `/api/personas`
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/personas/` | Alle Personas auflisten |
| GET | `/api/personas/{name}` | Einzelne Persona abrufen |
| POST | `/api/personas/` | Neue Persona erstellen |
| PUT | `/api/personas/switch` | Aktive Persona wechseln |
| DELETE | `/api/personas/{name}` | Persona löschen |

---

## Admin-API

Haupt-Backend mit allen Steuerungsfunktionen.

### Core
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/` | Root |
| GET | `/health` | Health-Check |
| GET | `/api/tags` | Modell-Tags |
| GET | `/api/tools` | Verfügbare Tools |
| GET | `/api/models/catalog` | Modell-Katalog |

### Chat — `/api/chat`
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| POST | `/api/chat` | Chat-Anfrage |

### Workspace — `/api/workspace`
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/workspace` | Alle Einträge |
| GET | `/api/workspace/{entry_id}` | Eintrag abrufen |
| PUT | `/api/workspace/{entry_id}` | Eintrag aktualisieren |
| DELETE | `/api/workspace/{entry_id}` | Eintrag löschen |
| GET | `/api/workspace-events` | SSE-Eventstream |

### Settings — `/api/settings`
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/settings/` | Alle Settings |
| POST | `/api/settings/` | Settings speichern |
| GET | `/api/settings/compression` | Komprimierungs-Einstellungen |
| POST | `/api/settings/compression` | Komprimierungs-Einstellungen setzen |
| GET | `/api/settings/master` | Master-Config |
| POST | `/api/settings/master` | Master-Config setzen |
| GET | `/api/settings/models` | Modell-Einstellungen |
| GET | `/api/settings/models/effective` | Effektive Modell-Config |
| POST | `/api/settings/models` | Modell-Einstellungen setzen |
| GET | `/api/settings/embeddings/runtime` | Embedding Runtime-Config |
| POST | `/api/settings/embeddings/runtime` | Embedding Runtime setzen |
| GET | `/api/settings/sequential/runtime` | Sequential Runtime-Config |
| POST | `/api/settings/sequential/runtime` | Sequential Runtime setzen |
| GET | `/api/settings/autonomy/cron-policy` | Cron-Policy abfragen |
| POST | `/api/settings/autonomy/cron-policy` | Cron-Policy setzen |
| GET | `/api/settings/reference-links` | Referenz-Links |
| POST | `/api/settings/reference-links` | Referenz-Links setzen |

### Protocol — `/api/protocol`
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/protocol/list` | Alle Protokolle auflisten |
| GET | `/api/protocol/today` | Heutiges Protokoll |
| GET | `/api/protocol/unmerged-count` | Anzahl ungemergte Einträge |
| GET | `/api/protocol/{date}` | Protokoll nach Datum |
| POST | `/api/protocol/append` | Eintrag hinzufügen |
| PUT | `/api/protocol/{date}` | Protokoll aktualisieren |
| DELETE | `/api/protocol/{date}/entry/{index}` | Eintrag löschen |
| POST | `/api/protocol/{date}/merge` | Protokoll mergen |
| POST | `/api/protocol/summarize-yesterday` | Gestern zusammenfassen |
| GET | `/api/protocol/rolling-summary` | Rolling Summary |

### Commander — Root-Pfade
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/blueprints` | Alle Blueprints |
| GET | `/blueprints/{blueprint_id}` | Blueprint abrufen |
| POST | `/blueprints` | Blueprint erstellen |
| PUT | `/blueprints/{blueprint_id}` | Blueprint aktualisieren |
| DELETE | `/blueprints/{blueprint_id}` | Blueprint löschen |
| POST | `/blueprints/import` | Blueprint importieren |
| GET | `/blueprints/{blueprint_id}/yaml` | Blueprint als YAML |
| POST | `/containers/deploy` | Container deployen |

### Secrets — `/api/secrets`
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/secrets` | Alle Secrets auflisten |
| POST | `/api/secrets` | Secret erstellen |
| PUT | `/api/secrets/{name}` | Secret aktualisieren |
| DELETE | `/api/secrets/{name}` | Secret löschen |
| GET | `/api/secrets/resolve/{name}` | Secret auflösen |

### Vault — Root-Pfade
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/status` | Vault-Status |
| POST | `/setup` | Vault initialisieren |
| POST | `/unlock` | Vault entsperren |
| POST | `/lock` | Vault sperren |
| GET | `/entries` | Alle Einträge |
| GET | `/entries/{entry_id}/password` | Passwort abrufen |
| POST | `/entries` | Eintrag erstellen |
| PUT | `/entries/{entry_id}` | Eintrag aktualisieren |
| DELETE | `/entries/{entry_id}` | Eintrag löschen |

### TRION Memory — Root-Pfade des Home-/Note-Memory
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| POST | `/trion/memory/remember` | Erinnerung im aelteren Home-/Note-Memory speichern |
| GET | `/trion/memory/recent` | Letzte Home-Memory-Eintraege |
| GET | `/trion/memory/recall` | Home-Memory abrufen |
| GET | `/trion/memory/status` | Home-Memory-Status |

Abgrenzung:

- dies ist nicht die WebUI-Memory-App unter `/api/memory/*`
- dieser Pfad arbeitet mit `identity_path` statt `conversation_id`
- die SQL-Conversation-Policy greift hier derzeit nicht automatisch
- die Implementierung liegt in `adapters/admin-api/home_note_memory.py`, nicht
  mehr unter `container_commander.*`

### Runtime — `/api/runtime`
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/runtime/compute/instances` | Compute-Instanzen |
| POST | `/api/runtime/compute/instances/{instance_id}/start` | Instanz starten |
| POST | `/api/runtime/compute/instances/{instance_id}/stop` | Instanz stoppen |
| GET | `/api/runtime/compute/routing` | Routing-Tabelle |
| POST | `/api/runtime/compute/routing` | Routing setzen |
| GET | `/api/runtime/digest-state` | Digest-Status |
| GET | `/api/runtime/session` | Session-Info |
| GET | `/api/runtime/autonomy-status` | Autonomie-Status |

### Runtime Hardware — `/api/runtime-hardware`
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/runtime-hardware/health` | Hardware Health |
| GET | `/api/runtime-hardware/connectors` | Verfügbare Konnektoren |
| GET | `/api/runtime-hardware/capabilities` | Hardware-Fähigkeiten |
| GET | `/api/runtime-hardware/resources` | Ressourcen-Übersicht |
| GET | `/api/runtime-hardware/targets/{target_type}/{target_id}/state` | Target-Status |
| POST | `/api/runtime-hardware/plan` | Hardware-Plan erstellen |
| POST | `/api/runtime-hardware/validate` | Hardware-Plan validieren |

### Storage Broker — `/api/storage-broker`
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/storage-broker/health` | Health-Check |
| GET | `/api/storage-broker/summary` | Speicher-Zusammenfassung |
| GET | `/api/storage-broker/settings` | Broker-Settings |
| POST | `/api/storage-broker/settings` | Broker-Settings setzen |
| GET | `/api/storage-broker/disks` | Alle Datenträger |
| POST | `/api/storage-broker/disks/{disk_id}/policy` | Disk-Policy setzen |
| GET | `/api/storage-broker/managed-paths` | Verwaltete Pfade |
| POST | `/api/storage-broker/validate-path` | Pfad validieren |
| POST | `/api/storage-broker/provision/service-dir` | Service-Verzeichnis anlegen |
| POST | `/api/storage-broker/mount` | Datenträger mounten |
| POST | `/api/storage-broker/unmount` | Datenträger unmounten |
| POST | `/api/storage-broker/format` | Datenträger formatieren |
| POST | `/api/storage-broker/partition` | Partition erstellen |
| GET | `/api/storage-broker/audit` | Audit-Log |
