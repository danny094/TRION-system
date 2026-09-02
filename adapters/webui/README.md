# TRION WebUI

Aktive WebUI fuer TRION. Dieses Verzeichnis enthaelt das Vite/React/TypeScript-Frontend, das im Browser laeuft und ueber `/api/*` mit der Admin API spricht.

Die WebUI ist kein eigener Python-Adapter mehr. Die alte Struktur mit `main.py` und separatem WebUI-Backend ist abgeloest.

## Stack

- React 19
- TypeScript
- Vite
- Zustand (State Management; `persist` nur in einzelnen Stores)
- Framer Motion (Animationen)
- dnd-kit (Drag & Drop)
- lucide-react (Icons)
- Tailwind CSS v4
- nginx (Container-Serve-Pfad)

## Entwicklung

Voraussetzungen:

- Node.js 22
- laufende Admin API auf `http://localhost:8200`

Lokaler Start:

```bash
npm ci
npm run dev
```

Die Dev-WebUI laeuft auf `http://localhost:3000`.
`/api/*` wird in `vite.config.ts` an die Admin API weitergereicht.

## Anmeldung und API-Sicherheit

`App.tsx` rendert `DesktopShell` ausschliesslich innerhalb des `AuthGate`.
Das Gate prueft `GET /api/auth/session`, zeigt bei Bedarf den zweisprachigen
Login fuer `POST /api/auth/login` und beendet die Session ueber
`POST /api/auth/logout`.

Der zentrale Client in `src/lib/api/client.ts` besitzt den Browservertrag:

- `credentials: same-origin` fuer alle `/api`-Requests,
- `x-csrf-token` fuer `POST`, `PUT`, `PATCH` und `DELETE`,
- ein Sessionverlust-Event bei `401`,
- einen rohen `Response`-Helper fuer den unveraenderten NDJSON-Chatstream.

Chat, Memory und Plugin-Host umgehen diesen Client nicht. Das Session-Cookie
ist `HttpOnly`/`SameSite=Strict`; mutierende Requests werden serverseitig
zusaetzlich gegen ihre lokale Origin geprueft.

## Build

```bash
npm run build
```

Das Produktions-Build landet in `dist/`.

## Docker

Es gibt ein Multi-Stage-Container-Setup in [Dockerfile](./Dockerfile):

- Build-Stage: `npm ci` und `npm run build`
- Runtime-Stage: `nginx:alpine`
- Container-Port: `3000`

[nginx.conf](./nginx.conf) uebernimmt:

- statisches Ausliefern von `dist/`
- SPA-Fallback auf `index.html`
- Proxy von `/api/*` nach `http://trion-admin-api:8200`
- `GET /health` fuer Healthchecks

## Struktur

Wichtige Pfade:

- `src/app/shell/`: DesktopShell – globale Shell, DnD-Kontext, Glow-Effekte
- `src/components/icons/`: zentraler Icon-Resolver (`AppIcon`)
- `src/components/layout/`: Dock, LaunchpadButton, SearchBar
- `src/components/windows/`: WindowManager, WindowFrame, ChatPanelFrame
- `src/features/chat/`: Chat, Session-Sidebar, NDJSON-Stream, Task-Loop-UI
- `src/features/auth/`: AuthGate, Browser-Session-Contract und Login-Styles
- `src/features/launchpad/`: App-Grid mit Drag-Sources
- `src/features/settings/`: Settings-Fenster mit 5 Tabs
- `src/lib/api/`: HTTP-Client
- `src/lib/contracts/`: App-Registry, Chat-Events (Contracts vor Logik)
- `src/lib/stream/`: NDJSON-Parser
- `src/state/`: windowStore, dockStore

Detaillierte Architektur-Doku: [webui-architektur.md](./webui-architektur.md)

## Chat und Task Loop

Der Chat arbeitet gegen die Admin API und verarbeitet den NDJSON-Event-Stream von `POST /api/chat`.

Aktueller Stand:

- Multi-Chat-Grundlage ist jetzt vorhanden
- die WebUI verwaltet mehrere Chat-Sessions innerhalb eines Chat-Fensters
- jede Session hat eine eigene `conversationId`
- normale Chat-Requests senden ohne explizite Modellwahl bewusst den Backend-Defaultpfad; die effektive Modellaufloesung bleibt serverseitig
- Persistenz, Backend-History und Auto-Titel bleiben bewusst spaetere Ausbaustufen

Relevante Event-Typen fuer die UI:

- `content`
- `error`
- `blocked`
- `rejected`
- `classifier_result`
- `thinking_plan`
- `verifier_result`
- `tool_start`
- `tool_result`
- `task_loop_state`
- `task_loop_waiting`
- `done`

Sichtbares Thinking im Chat:

- Assistant-Nachrichten koennen jetzt eine aufklappbare `Visible Thinking`-Karte
  anzeigen
- diese Karte rendert die echte Pipeline-Spur aus `classifier_result`,
  `thinking_plan` und `verifier_result`
- die WebUI erzeugt dabei keine zweite Wahrheit und kein eigenes Planning,
  sondern zeigt nur den gestreamten Contract an
- wenn der Core eine enge Folgearbeit auf verifizierter Wahrheit erkannt hat,
  zeigt die Karte zusaetzlich `Projection`, `Derivation` und einen moeglichen
  `Additional evidence needed`-Hinweis aus dem echten `thinking_plan`

Die Task-Loop-Darstellung lebt im Chat-Feature und zeigt insbesondere:

- `waiting`
- `replanning`
- `cancelled`
- `blocked`

Bei `task_loop_waiting` kann die UI ueber `POST /api/tasks/{task_id}/approve` fortsetzen.

## Settings

Das Settings-Fenster (Einstellungen) hat 5 Tabs:

| Tab | Inhalt |
|---|---|
| Allgemein | Systemsprache, Autostart |
| KI & Verhalten | Persona plus 6 Autonomie-Bereiche; Persona via `/api/personas/*`, die übrigen Bereiche via `GET/POST /api/settings/autonomy/profile` mit Live-Speichern ohne Rebuild |
| Erscheinungsbild | Theme, Layout |
| Modelle | Layer-Zuweisung: Thinking / Control / Output mit Provider + Modell |
| API | API-Schlüssel verwalten (hinzufügen, anzeigen, löschen) |

Modelle und API sprechen direkt gegen die Admin API:

- `GET /api/models/catalog`
- `GET /api/settings/models/effective`
- `POST /api/settings/models`
- `GET /api/personas/`
- `GET /api/personas/{name}`
- `PUT /api/personas/content/{name}`
- `PUT /api/personas/switch?name=...`
- `GET /api/settings/autonomy/profile`
- `POST /api/settings/autonomy/profile`
- `GET /api/settings/api-keys`
- `POST /api/settings/api-keys`
- `DELETE /api/settings/api-keys/{id}`

Im API-Tab zeigt ein anklickbares `?`, unter welchen Key-Namen der Backend-Resolver
Cloud-Provider automatisch lesen kann, z. B. `OLLAMA_API_KEY`,
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY` und ihre unterstuetzten Alias-Namen.
Die Aufloesung erfolgt aus dem verschluesselten Provider-Key-Store der Admin API, nicht aus Container-ENV-Variablen.

## Design-Hinweise

Die WebUI folgt den Repo-Regeln aus [docs/governance/07-design-rules.md](../../docs/governance/07-design-rules.md) und den UI-spezifischen Regeln in [webui-design-regeln.md](./webui-design-regeln.md).

Wichtige Leitplanken:

- keine Altpfade oder Archivordner im aktiven Frontend
- max. 200 Zeilen pro Datei
- Contracts vor Logik
- kein Backend-State erfinden – UI zeigt nur bestätigte Events
- Farbe hat Bedeutung (Blau=Chat, Grün=Memory, Orange=Tools, Rot=Fehler, Gelb=Warnung)

## Verwandte Docs

- [webui-architektur.md](./webui-architektur.md) ← interner Aufbau, State, Drag-to-Dock, Features erweitern
- [webui-design-regeln.md](./webui-design-regeln.md)
- [docs/adapters/17-webui-api-endpoints.md](../../docs/adapters/17-webui-api-endpoints.md)
- [docs/task-loop/18-autonomous-tool-execution.md](../../docs/task-loop/18-autonomous-tool-execution.md)
- [docs/reference/08-deployment.md](../../docs/reference/08-deployment.md)
