# TRION WebUI – Architektur

← [README](./README.md) | [Design-Regeln](./webui-design-regeln.md)

> Dieses Dokument beschreibt den internen Aufbau der TRION WebUI.
> Es richtet sich an Entwickler, die den Code verstehen, erweitern oder debuggen wollen.

---

## Grundprinzip

Die WebUI ist eine **lokale AI-OS-Shell**, kein Admin-Panel und keine einfache Chat-Seite.

Sie ist modular aufgebaut:

```
App.tsx
└── AuthGate              ← Login, Sessionprüfung und Logout
    └── DesktopShell      ← globale Shell, DnD-Kontext, Glow-Effekte, Right-Click
        ├── WindowManager     ← rendert alle offenen Fenster + Minimize-Tray
        ├── LaunchpadButton   ← Quick-Launch-Buttons unten links
        ├── DesktopClock      ← Uhr oben rechts
        ├── Dock              ← gepinnte Apps, sortierbar, Drop-Zone
        ├── DesktopContextMenu ← Rechtsklick-Menü auf den Desktop
        └── SearchBar         ← globale Suche oben
```

Die Shell verdrahtet nur UI und Navigation.  
Sie trifft **keine Runtime-Entscheidungen** und erfindet keinen Backend-State.

---

## Ordnerstruktur

```
src/
├── App.tsx                         ← Einstieg, mountet DesktopShell
├── main.tsx                        ← React-Root, Font-Import
├── index.css                       ← globale CSS-Variablen, glass-Utility
│
├── app/
│   └── shell/
│       └── DesktopShell.tsx        ← Shell-Root: DndContext, Glow, Layout
│
├── components/
│   ├── icons/
│   │   └── AppIcon.tsx             ← zentraler Icon-Resolver (custom SVGs aus assets/icons/)
│   ├── layout/
│   │   ├── Dock.tsx                ← Drop-Zone + sortierbare Dock-Items
│   │   ├── LaunchpadButton.tsx     ← Quick-Launch: Launchpad + Chat
│   │   ├── DesktopClock.tsx        ← Uhr oben rechts (HH:MM + Datum)
│   │   ├── DesktopContextMenu.tsx  ← Rechtsklick-Menü (Apps + Hintergrund-Reset)
│   │   └── SearchBar.tsx           ← globale Suchleiste
│   └── windows/
│       ├── WindowFrame.tsx         ← draggbarer Fensterrahmen + Snap-Logik
│       ├── ResizeHandles.tsx       ← 8-Richtungs-Resize (N/NE/E/SE/S/SW/W/NW)
│       ├── SnapPreview.tsx         ← Snap-Preview-Overlay (Portal in document.body)
│       ├── ChatPanelFrame.tsx      ← Chat-Panel (Sonderrahmen, rechts angedockt)
│       └── WindowManager.tsx       ← rendert alle windows[] + Minimize-Tray
│
├── features/
│   ├── auth/
│   │   ├── contracts.ts           ← Principal-, Ablauf- und CSRF-Metadaten
│   │   ├── AuthGate.tsx           ← Sessionprüfung, Login und Logout
│   │   └── AuthGate.css           ← Login-/Sessiondarstellung
│   │
│   ├── chat/
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── ChatSessionSidebar.tsx
│   │   │   ├── ChatHeader.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   ├── ChatMessageList.tsx
│   │   │   └── TaskLoopStatusCard.tsx
│   │   ├── lib/
│   │   │   ├── sessionFactory.ts
│   │   │   └── sessionSelectors.ts
│   │   ├── state/
│   │   │   └── chatStore.ts        ← Sessions, activeSession, sendMessage, approveWaitingTask
│   │   ├── types.ts                ← ChatSession, Message, SessionId
│   │   └── api.ts                  ← sendMessageStream, approveTask
│   │
│   ├── launchpad/
│   │   └── components/
│   │       └── LaunchpadWindow.tsx ← App-Grid, Drag-Sources aus APP_REGISTRY
│   │
│   ├── modelle/
│   │   └── ModelleWindow.tsx       ← Placeholder-Fenster für Modelle-App
│   │
│   ├── mcps/
│   │   ├── api.ts                  ← fetchInstalledMcps, installMcp, toggleMcp, uninstallMcp
│   │   ├── state/
│   │   │   └── mcpsStore.ts        ← items, installerView ('about'|'all'|'install'|'uninstall'|'files'|'news')
│   │   └── components/
│   │       ├── McpsWindow.tsx          ← Shell mit Tab-Routing
│   │       ├── McpsSidebar.tsx         ← 6-Tab-Navigation, Icon-Card-Header, Runtime-Status-Footer
│   │       ├── AddMcpModal.tsx         ← ZIP-Upload-Modal (Fallback-Picker)
│   │       ├── McpDetail.tsx           ← Detail-Panel (legacy, nicht im Tab-Layout aktiv)
│   │       ├── McpListItem.tsx         ← Listen-Eintrag (legacy)
│   │       ├── McpsListView.tsx        ← Listen-View (legacy)
│   │       ├── McpManifestView.tsx     ← Manifest-Anzeige (legacy)
│   │       ├── McpActions.tsx          ← Toggle/Remove-Buttons (legacy)
│   │       └── views/
│   │           ├── AboutView.tsx       ← Tab „About" (Welcome + Sources-Card + Stats)
│   │           ├── AllView.tsx         ← Tab „All" (Server-Table + Filter-Chips + Search)
│   │           ├── InstallView.tsx     ← Tab „Install" (ZIP-Drop links, GitHub-Card rechts, Options-Footer)
│   │           ├── UninstallView.tsx   ← Tab „Uninstall" (Multi-Select-Table + Batch-Footer)
│   │           ├── ConfirmRemoveModal.tsx ← Shared Confirm-Dialog für Single + Batch-Remove
│   │           ├── FilesView.tsx       ← Tab „Files" (~/.trion/mcp Browser, Mock-Daten bis Backend)
│   │           └── NewsView.tsx        ← Tab „News" (statischer Changelog mit Release-Badges)
│   │
│   └── settings/
│       ├── api.ts                  ← Modelle: fetchModelCatalog, updateModelSettings
│       ├── apiKeysApi.ts           ← API-Keys: fetchApiKeys, addApiKey, deleteApiKey
│       ├── personaApi.ts           ← Persona: fetchPersonas, fetchPersona, updatePersona, switchPersona
│       ├── personaEditor.ts        ← Persona-Parsing + Build (parsePersonaContent, buildPersonaContent)
│       ├── providerSettingsHelpers.ts ← ROLE_CONFIGS, RoleState, dedupeModelNames, errorMessage
│       └── components/
│           ├── SettingsWindow.tsx        ← Tab-Shell: Icon-Card-Header, 5 Tabs, OSX-Style farbige Tab-Quadrate
│           ├── KiVerhaltenPanel.tsx      ← Tab „KI & Verhalten": macOS-List-Navigation, State-Lift für 7 Sub-Views
│           ├── GeneralPanel.tsx          ← Tab „Allgemein": Textgröße + Hintergrundbild (je Card)
│           ├── AppearancePanel.tsx       ← Tab „Erscheinungsbild": Akzentfarbe (Card)
│           ├── ProviderSettingsPanel.tsx ← Tab „Modelle": Layer-Zuweisung, Header + Banner
│           ├── RoleCard.tsx              ← Thinking/Control/Output-Card mit Provider/Modell-Select
│           ├── ApiKeysPanel.tsx          ← Tab „API": Schlüssel verwalten (Add-Card)
│           ├── ApiKeysTable.tsx          ← Tabelle der gespeicherten Keys mit Hover-Delete
│           ├── ApiKeyNamingHelp.tsx      ← Resolver-Hilfe für akzeptierte Key-Namen
│           └── views/ki/
│               ├── DetailHeader.tsx           ← Shared Back-Button-Header für alle KI-Sub-Views
│               ├── PersonaPanel.tsx           ← Sub-View „Persona" (Editor + API-Calls)
│               ├── ArbeitsmodusPanel.tsx      ← Sub-View „Arbeitsmodus" (Manuell/Halbautomatisch/Autonom)
│               ├── PlanungstiefePanel.tsx     ← Sub-View „Planungstiefe" (Schnell/Normal/Gründlich/Unbegrenzt)
│               ├── WarteVerhaltenPanel.tsx    ← Sub-View „Warteverhalten" (Sofort/30 Sek/2 Min/Immer)
│               ├── SicherheitsebenePanel.tsx  ← Sub-View „Sicherheitsebene" (Toggles + Locked-Row)
│               ├── FehlerVerhaltenPanel.tsx   ← Sub-View „Fehlerverhalten" (Radio-Buttons)
│               └── SchleifenerkennungPanel.tsx ← Sub-View „Schleifenerkennung" (Toggle + Empfindlichkeit)
│
├── lib/
│   ├── api/
│   │   └── client.ts               ← same-origin Credentials, CSRF, 401-Signal, Response-Helper
│   ├── contracts/
│   │   ├── appRegistry.ts          ← APP_REGISTRY: alle Apps + ihre Window-Configs
│   │   └── chatEvents.ts           ← typisierte Chat-Event-Contracts vom Backend
│   ├── stream/
│   │   └── ndjsonParser.ts         ← NDJSON-Stream → AsyncIterable<ChatEvent>
│   └── utils.ts                    ← cn() Helper (clsx + tailwind-merge)
│
└── state/
    ├── windowStore.ts              ← alle offenen Fenster, focus, minimize, z-Index
    ├── dockStore.ts                ← gepinnte Dock-Apps, persistent (localStorage)
    └── uiStore.ts                  ← UI-Präferenzen: fontSize, backgroundImage, accentColor (persistent)
```

---

## Browser-Authentisierung

`AuthGate` ist der einzige Einstieg in `DesktopShell`. Es bezieht
Principal-, Ablauf- und CSRF-Metadaten aus `/api/auth/session`; Credential und
Session-Key bleiben serverseitig. Der zentrale API-Client sendet Cookies nur
same-origin und fuegt `x-csrf-token` nur mutierenden Methoden hinzu. Die Admin
API prueft dazu die lokale Origin. Chat-, Memory- und Plugin-Host-Requests
nutzen denselben Client; der rohe Response-Pfad fuer NDJSON bleibt erhalten.

---

## Import-Richtung

```
components/icons/    ← importiert nichts außer @/assets/icons/ und @/lib/utils
components/layout/   ← importiert icons/, state/
components/windows/  ← importiert layout/, features/, state/
features/            ← importiert components/, lib/, state/
lib/                 ← importiert keine UI-Komponenten
state/               ← importiert contracts/, keine Komponenten
app/                 ← verdrahtet Shell, Provider, Features
```

**Keine Kreis-Importe. Features importieren nie andere Features direkt.**

---

## State-Architektur

State ist klar nach Domäne getrennt:

| Store | Ort | Inhalt | Persistenz |
|---|---|---|---|
| `windowStore` | `state/` | alle offenen Fenster, position, zIndex, focus, minimized, maximized | nein (Session) |
| `dockStore` | `state/` | gepinnte Dock-Apps | **ja** (`trion-dock`) |
| `uiStore` | `state/` | fontSize, backgroundImage, accentColor, dockAutoHide | **ja** (`trion-ui`) |
| `chatStore` | `features/chat/state/` | Chat-Sessions, aktive Session, Nachrichten, Stream-Status, conversationId pro Session | nein (Session) |

### windowStore

Verwaltet `WindowState[]`. Jedes Fenster hat:

```ts
windowId, appId, title, position, size, zIndex, minimized, maximized, focused, displayMode
```

Singleton-Apps (`chat`, `launchpad`, `settings`) können nicht doppelt geöffnet werden –
bei erneutem Öffnen wird das bestehende Fenster fokussiert.

### dockStore

Persistenter Store (Zustand `persist`-Middleware, `trion-dock` Key).  
`hasApp(id)` verhindert Duplikate beim Pinnen aus dem Launchpad.

### chatStore

Verwaltet `ChatSession[]` + `activeSessionId`.  
Kommuniziert mit der Admin API via `sendMessageStream()` (NDJSON-Stream).  
Task-Approval läuft über `approveWaitingTask()` → `POST /api/tasks/{id}/approve`.

Aktueller Multi-Chat-Schnitt:

- mehrere Sessions innerhalb eines Chat-Fensters
- jede Session hat eigene `messages`, `isBusy`, `conversationId`
- Session-Wechsel, Session-Schliessen und `Neuer Chat` sind rein lokaler UI-State
- keine Persistenz und kein Backend-History-Load in dieser Phase

**Sidebar-Collapse:** Die `ChatSessionSidebar` lässt sich ein- und ausklappen (Chevron-Toggle).
`ChatWindow` beobachtet die Container-Breite per `ResizeObserver` und klappt automatisch ein,
wenn das Chat-Fenster schmaler als 520px wird (z.B. im 420px Panel-Modus). Sobald der User
manuell togglet, wird das Auto-Verhalten für die Session deaktiviert (User-Override).
Eingeklappt zeigt die Sidebar einen 40px schmalen Strip mit `+`-Button und Punkten pro Session.

### uiStore

Persistenter Store (`trion-ui` Key) für globale UI-Präferenzen:

```ts
fontSize: 'sm' | 'md' | 'lg' | 'xl'   // → setzt <html> font-size in px
backgroundImage: string | null         // base64-DataURL für Desktop-Hintergrund
accentColor: string                    // Hex, wird live als --color-primary auf <html> gesetzt
dockAutoHide: boolean                  // (vorbereitet, noch nicht aktiv)
```

`DesktopShell.tsx` reagiert per `useEffect` auf Änderungen und überträgt sie ins DOM —
keine Backend-Calls, alles rein im Browser.

---

## Fenster-System

### Öffnen

```ts
openWindow({ appId: 'settings', title: 'Einstellungen', size: { width: 800, height: 560 } })
```

Der `windowStore` erzeugt eine `windowId`, setzt `zIndex`, `focused: true`.

### Rendern

`WindowManager` iteriert `windows[]` und entscheidet:

```
appId === 'chat'         → ChatPanelFrame  (Panel-Modus, rechts angedockt)
appId === 'settings'     → SettingsWindow  in WindowFrame
appId === 'launchpad'    → LaunchpadWindow in WindowFrame
appId === 'api-settings' → ApiKeysPanel    in WindowFrame
appId === 'modelle'      → ModelleWindow   in WindowFrame (Placeholder)
appId === 'mcp'          → McpsWindow      in WindowFrame (6-Tab-Layout)
sonst                    → Platzhalter in WindowFrame
```

### Settings – 5 Tabs

App-ID `settings`, Window-Titel `Einstellungen`, Default-Größe `800×560`. Linke Sidebar
mit Icon-Card-Header („Einstellungen / v 1.0 · TRION"), 5 Tabs mit kleinen farbigen
Icon-Quadraten im macOS-System-Settings-Stil (Allgemein grau, KI & Verhalten lila,
Erscheinungsbild rosa, Modelle blau, API amber). Active-Tab-Stil ist die gleiche
dezente weiße Pille wie im MCP Installer — kein Gold in der Nav. Content-Bereich nutzt
das einheitliche „Eyebrow / großer Titel / Subtitle"-Header-Pattern; Sections sitzen in
`rounded-2xl border-white/6 bg-white/[0.02]` Cards. Padding `px-8 py-7`.

| Tab | Komponente | Status | Inhalt |
|---|---|---|---|
| Allgemein | `GeneralPanel` | ✅ aktiv | Textgröße (4 Stufen) + Hintergrundbild-Upload, je als Card |
| KI & Verhalten | `KiVerhaltenPanel` + 7 Sub-Views in `views/ki/` | ✅ aktiv | macOS-List-Navigation: Persona, Arbeitsmodus, Planungstiefe, Warteverhalten, Sicherheitsebene, Fehlerverhalten, Schleifenerkennung. Persona via `/api/personas/*`; die übrigen 6 Bereiche hängen jetzt an `GET/POST /api/settings/autonomy/profile` und mappen serverseitig auf Runtime-Keys. |
| Erscheinungsbild | `AppearancePanel` | ✅ aktiv | Akzentfarbe (6 Presets + Color-Picker) als Card |
| Modelle | `ProviderSettingsPanel` + `RoleCard` | ✅ aktiv | `GET /models/catalog`, `GET/POST /settings/models` — pro Layer (Thinking/Control/Output) eine RoleCard |
| API | `ApiKeysPanel` + `ApiKeysTable` | ✅ aktiv | `GET/POST /settings/api-keys`, `DELETE /settings/api-keys/{id}` — Add-Card + Table |

API-Calls bleiben unverändert über `features/settings/api.ts` und `features/settings/apiKeysApi.ts`;
der OSX-Redesign war rein visuell.

### MCP Installer – 6 Tabs

App-ID `mcp`, Window-Titel `MCP Installer`, Default-Tab `'about'`. Linke Sidebar mit
weißem Icon-Card-Header („MCP Installer / v 1.0 · TRION"), 6 Tabs ohne destruktive
Sonderbehandlung in der Nav, unten Runtime-Status-Indikator („● X active /
connected to runtime"). Active-Tab-Stil ist subtil hellgrau (kein Gold), damit der
Installer wie eine eigene kleine App wirkt. State (`installerView`) liegt im
`mcpsStore`. Die Bundle-Contract- und Endpunkte-Wahrheit liegt im
[Backend-Doc](../../docs/mcp/21-mcp-installer.md).

| Tab | Komponente | Status | Inhalt |
|---|---|---|---|
| About | `AboutView` | ✅ wired | Welcome-Block, „Supported sources"-Card (GitHub + ZIP/TAR), „What it does"-Bullets, Stats-Footer (Installed / Active / Offline) |
| All | `AllView` | ✅ wired | Server-Table, Filter-Chips (Installed / Online / Offline mit Counts), Search-Input, Sort-Dropdown, Online/Offline-Toggle pro Row. Size + Version zeigen `—` bis Backend-Felder ergänzt sind. |
| Install | `InstallView` | ✅ wired | Split-Layout: ZIP/TAR-Drop-Zone links, GitHub-Card rechts (URL + Branch-Input, Install-Button mit `soon`-Badge), Footer-Bar mit 3 Toggle-Optionen (Auto-enable / Run health-check / Pin to dock) + Install-Path-Anzeige |
| Uninstall | `UninstallView` | ✅ wired | Multi-Select-Table mit Header-Checkbox-All, Row-Trash für Single-Remove, Footer „X selected · Uninstall selected". Confirm via `ConfirmRemoveModal` (Single + Batch). |
| Files | `FilesView` | UI-only | Path-Header (`~/.trion/mcp`), Upload + New Buttons, Search, File-Liste mit tint-gefärbten Icons (yaml=lila, dockerfile=teal, env=rot). Mock-Daten in `MOCK_FILES`-Konstante bis Backend-Endpunkt liefert. |
| News | `NewsView` | ✅ static | Statischer Changelog mit RELEASE/UPDATE/ADDED/FIXED-Badges (pastel grün/blau/lila/grau). Editorial Content in `CHANGELOG`-Konstante. |

Zusätzlich host-managed aus MCP-Metadaten:
- `ui.icon` → generischer `/api/mcp/{name}/icon`-Pfad, genutzt in `AllView`, `UninstallView`, Launchpad und Dock
- `ui.launchpad.enabled` → dynamischer Host-App-Eintrag über `mcpHostApps.ts`
- `ui.settings.enabled` → Klick auf Host-App öffnet `McpSettingsWindow` mit generischem Config-Editor (`PUT /api/mcp/{name}/config`)
- `mcp.json` ist das Ziel-Manifest; der Settings-Editor schreibt denselben Manifest-Contract zurück, den auch der Installer beim Upload validiert

API-Calls weiterhin unverändert über `useMcpsStore`:
- Upload → `uploadBundle(file)` → `POST /api/mcp/install`
- Toggle (All-Tab) → `POST /api/mcp/{name}/toggle`
- Remove (Uninstall-Tab) → `DELETE /api/mcp/{name}`
- Refresh überall → `GET /api/mcp/list`
- MCP-Settings → `GET /api/mcp/{name}/details`, `PUT /api/mcp/{name}/config`, `GET /api/mcp/{name}/icon`

Install-Options (Auto-enable / Health-check / Pin-to-dock) liegen aktuell als
lokales `useState` in `InstallView` und werden noch nicht an den Install-Call
weitergereicht — Backend-Erweiterung in Vorbereitung.

### Fensterrahmen

`WindowFrame` ist ein draggbarer Framer-Motion-Container mit:
- Titelleiste (Drag-Handle, Doppelklick togglet Maximize)
- Minimize / Maximize / Close Buttons
- Fokus-Management per `onPointerDown`
- **Resize-Handles**: 8 Richtungen (`ResizeHandles.tsx`), Mindestgröße 300×200px, deaktiviert wenn maximiert
- **Snap-Zonen**: links/rechts/oben (`SNAP_EDGE = 40px`), zeigt `SnapPreview`-Overlay während des Drags
- **Minimize-Tray**: minimierte Fenster werden in `WindowManager` als Pill-Buttons über dem Dock gerendert (Klick → Wiederherstellen)

`ChatPanelFrame` ist eine Variante für den Chat – ohne Resize/Maximize, fixe rechte Position.

---

## Drag-to-Dock System

### Beteiligte Komponenten

```
DesktopShell          ← globaler DndContext (pointerWithin)
├── LaunchpadWindow   ← App-Icons: useDraggable (data: { appId })
└── Dock              ← useDroppable (id: 'dock-drop-zone')
    └── SortableDockItem ← useSortable (interne Sortierung)
```

### Flow

1. User öffnet Launchpad-Fenster
2. Zieht ein App-Icon auf den Dock
3. `DragOverlay` zeigt ein Ghost-Icon (floating, folgt Maus)
4. Dock leuchtet golden bei `isOver`
5. `onDragEnd` in `DesktopShell` prüft:
   - `over?.id === 'dock-drop-zone'`
   - `def.canPin === true`
   - `!hasApp(appId)` (kein Duplikat)
6. → `addApp()` in `dockStore`

### Regeln (laut Design-Regeln)

- Drag verändert **nur Layout-State** – keine Runtime-Aktionen
- Dock-Items sind klickbar → öffnen das Fenster der App
- Interne Sortierung per `useSortable` (Reihenfolge im dockStore)
- Entfernen per X-Button (Hover) → `removeApp(id)`
- Dock-Position wird **persistent** gespeichert

---

## App-Registry

`lib/contracts/appRegistry.ts` ist die Wahrheit für **statische Host-Apps**.
Installer-owned MCP-Host-Apps werden zusätzlich zur Laufzeit aus
`lib/contracts/mcpHostApps.ts` abgeleitet.

```ts
APP_REGISTRY: AppDefinition[] = [
  { id: 'launchpad',    label: 'Launchpad',     iconName: 'launchpad',    canPin: false, ... },
  { id: 'chat',         label: 'Chat',          iconName: 'chat',         canPin: true,  ... },
  { id: 'settings',     label: 'Einstellungen', iconName: 'settings',     canPin: true,  ... },
  { id: 'api-settings', label: 'API Settings',  iconName: 'api-settings', canPin: true,  ... },
  { id: 'modelle',      label: 'Modelle',       iconName: 'modelle',      canPin: true,  ... },
  { id: 'mcp',          label: 'MCP Installer', iconName: 'mcp',          canPin: true,  ... },
]
```

Jede `AppDefinition` enthält:
- `id` – eindeutige App-ID (kebab-case)
- `label` – Anzeigename
- `iconName` – Key für `ICON_MAP` in `AppIcon.tsx` (entspricht SVG-Dateiname ohne Prefix/Extension)
- `color` – Tailwind-Farbklasse (z.B. `text-blue-400`)
- `openArgs` – alles was `openWindow()` braucht
- `canPin` – ob die App in den Dock gezogen werden darf

Aktueller Stand:
- `launchpad` ist registriert, aber bewusst `canPin: false`, weil es als fester Quick-Launch unten links lebt
- `chat`, `settings`, `api-settings`, `modelle` und `mcp` können aus dem Launchpad in den Dock gepinnt werden
- `modelle` öffnet derzeit ein Placeholder-Fenster
- `mcp` öffnet das vollwertige Tab-Layout (About / All / Install / Uninstall / Files / News)

**Neue App hinzufügen:** Eintrag in `APP_REGISTRY` + Icon in `AppIcon.tsx` registrieren + Feature in `WindowManager` rendern.

---

## Icon-System

Icons sind **eigene SVG-Dateien**, erstellt in Affinity Designer und exportiert als SVG für Web.

### Ablageort

```
src/assets/icons/
├── icon-settings.svg
├── icon-chat.svg
├── icon-launchpad.svg
├── icon-erscheinungsbild.svg
├── icon-modelle.svg
├── icon-api-settings.svg
└── icon-mcp.svg
```

Weitere Icons (z.B. `icon-terminal.svg`, `icon-storage.svg`, `icon-Plugins.svg`) liegen
bereits im Ordner, sind aber noch nicht über `APP_REGISTRY` an Apps gebunden.

### AppIcon-Komponente

`components/icons/AppIcon.tsx` importiert alle SVGs statisch und mappt sie über `ICON_MAP`:

```ts
const ICON_MAP: Record<string, string> = {
  'settings':         iconSettings,
  'chat':             iconChat,
  'launchpad':        iconLaunchpad,
  'erscheinungsbild': iconErscheinungsbild,
  'modelle':          iconModelle,
  'api-settings':     iconApiSettings,
  'mcp':              iconMcp,
}
```

Die Komponente rendert ein `<img>` Tag mit `object-cover`. Größenverwendung im Layout:

- **Launchpad-Kachel** und **Dock-Tile**: Icon füllt die gesamte 56×56px Kachel (`w-full h-full`, `rounded-2xl overflow-hidden`) — kein Glass-Wrapper, der das Icon einrahmt
- **Drag-Ghost**: identisch zur Dock-Tile, mit goldenem Glow-Shadow
- **Settings-Sidebar**: kleiner skaliert (`w-6 h-6`)
- **Minimize-Tray**: noch kleiner (`w-3.5 h-3.5`)

### Ausnahme: KI & Verhalten

Für diesen Tab existiert noch kein eigenes Icon – hier wird vorerst das Lucide-Icon `<Cpu>` verwendet. Sobald `icon-ki-verhalten.svg` in `src/assets/icons/` abgelegt wird, kann es in `AppIcon.tsx` ergänzt und in `SettingsWindow.tsx` eingebunden werden.

### Neues Icon hinzufügen

1. SVG exportieren (Affinity: „SVG für Web", transparent, Viewbox aktiv)
2. Datei nach `src/assets/icons/icon-<name>.svg` legen
3. In `AppIcon.tsx` importieren und in `ICON_MAP` eintragen
4. `iconName: '<name>'` in `appRegistry.ts` oder direkt in der Komponente verwenden

---

## Chat & Stream

### API-Flow

```
ChatInput
  → chatStore.sendMessage()
    → api.sendMessageStream()       ← POST /api/chat
      → lib/stream/ndjsonParser.ts  ← AsyncIterable<ChatEvent>
        → for await (event of stream)
          → chatStore State-Update
            → ChatMessageList re-rendert
```

### Event-Typen

Definiert in `lib/contracts/chatEvents.ts`:

| Event | Bedeutung |
|---|---|
| `content` | Streaming-Text-Fragment |
| `done` | Lauf abgeschlossen (mit `done_reason`) |
| `error` | Fehler aus der Pipeline |
| `blocked` | Sicherheits-Block |
| `rejected` | Explizit abgelehnt |
| `task_loop_state` | Task-Loop-Statusänderung |
| `task_loop_waiting` | Wartet auf User-Approval |
| `tool_start` / `tool_result` | Tool-Ausführung |

`task_loop_waiting` aktiviert den Approve-Button → `POST /api/tasks/{task_id}/approve`.

---

## Features erweitern

### Neue App hinzufügen

1. `lib/contracts/appRegistry.ts` – Eintrag in `APP_REGISTRY`
2. SVG-Icon nach `src/assets/icons/icon-<name>.svg` legen (Affinity: SVG für Web, transparent)
3. `components/icons/AppIcon.tsx` – SVG importieren + in `ICON_MAP` eintragen
4. `features/<app-name>/components/<App>Window.tsx` – Feature-Komponente bauen
5. `components/windows/WindowManager.tsx` – `appId` Case hinzufügen
6. Optional: `state/windowStore.ts` – als Singleton registrieren

### Neuen Tab in Settings hinzufügen

`features/settings/components/SettingsWindow.tsx` – `TABS`-Array erweitern + `EmptyTabContent` füllen.

---

## Farbsystem

Farben haben Bedeutung (laut Design-Regeln):

| Farbe | Bedeutung |
|---|---|
| `text-blue-400` | Chat / Kommunikation |
| `text-green-400` | Memory / Persistenz / Gesund |
| `text-orange-400` | Tools / Aktionen / Wartung |
| `text-purple-400` | Logs / Analyse / System |
| `text-red-400` | Fehler / Block / Risiko |
| `text-yellow-400` | Warnung / Approval / Aufmerksamkeit |
| `text-white/70` | Neutral / System (z.B. Settings) |

---

## Bekannte Lücken (offen)

Status-Wahrheit für MCP-Installer-Lücken: [`docs/mcp/21-mcp-installer.md`](../../docs/mcp/21-mcp-installer.md)
unter „Aktuelle Grenzen". Hier nur die WebUI-seitige Sicht.
Es besteht kein aktueller Runtime-PASS.

| Was | Status |
|---|---|
| Settings – KI & Verhalten Budget-/Preset-Feinschnitt | `GET/POST /api/settings/autonomy/profile` ist aktiv, aber Token-/Kostenbudgets, Experten-Regler und feinere Trigger-Schwellen sind noch nicht im Host-Tab verdrahtet |
| Settings – KI & Verhalten Budget-/Preset-Steuerung | eigener Runtime-/Budget-Tab oder Plugin fuer feineres Task-Loop-/Token-Wiring noch offen |
| Settings – API-Key-Test/Health pro Provider | offen |
| Modelle-App (separates Fenster, nicht der Settings-Tab) | Placeholder-Window vorhanden, Inhalt offen |
| MCP Installer – GitHub-Install | UI mit `soon`-Badge vorhanden, Backend-Pfad offen |
| MCP Installer – Files-Tab Backend | UI zeigt Mock-Daten aus `MOCK_FILES`, Listing-Endpunkt offen |
| MCP Installer – Install-Optionen-Wiring | Toggle-State (Auto-enable/Health-check/Pin to dock) in `InstallView` lokal, noch nicht an `POST /api/mcp/install` weitergereicht |
| MCP Installer – Marktplatz-Suche | als eigene App geplant, weder UI noch Registry-Eintrag vorhanden |
| Eigenes Icon für „KI & Verhalten" | Lucide-Fallback (`<Cpu>`), bis SVG vorliegt |
| Dock Auto-Hide | im `uiStore` vorbereitet (`dockAutoHide`), Logik im Dock noch nicht aktiv |
| Weitere Apps im Launchpad | `APP_REGISTRY` bereit für Erweiterung |
| Command Palette | nicht implementiert |
| Notification Center | nicht implementiert |
| Plugin-System | siehe [[22-plugins]], initial fuer `launchpad`- und `settings.tab`-Mounts implementiert; HTML laeuft im opaque-origin iframe ohne `allow-same-origin`, `.js`/`.mjs` bleibt blockiert und authentisierte Parent-Mediation folgt erst in P16-SP4 |
