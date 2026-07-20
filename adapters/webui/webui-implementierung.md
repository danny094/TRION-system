# TRION WebUI — Implementierungsliste

Gesammelte Frontend-Verbesserungen. Kein Backend wird angefasst.
Alle Änderungen sind rein lokal im Browser (Zustand + persist) oder DOM-seitig.

---

## Status-Legende

- `[ ]` Offen
- `[~]` In Arbeit
- `[x]` Fertig

---

## 1. Drag & Drop — Fix

**Status:** `[x]`

**Problem:**
- `DesktopShell.handleDragEnd` verarbeitet nur das Hinzufügen aus dem Launchpad, nicht die Dock-interne Sortierung.
- Der `onSortEnd`-Callback in `SortableDockItem` wird übergeben aber nie aufgerufen — Verbindung zur `DndContext`-Ebene fehlt.
- Wenn ein Launchpad-Icon über ein bestehendes Dock-Item fallengelassen wird, ist `event.over?.id` die `app.id` des Dock-Items statt `DOCK_DROP_ID` → Drop schlägt still fehl.

**Lösung:**
- `handleDragEnd` in `DesktopShell.tsx` um Sortierlogik erweitern.
- Dock-Drop auch dann auslösen, wenn `over?.id` auf ein existierendes Dock-Item zeigt (nicht nur auf `DOCK_DROP_ID`).
- Sortierung über `reorderApps` im `dockStore` auslösen.

**Betroffene Dateien:**
- `src/app/shell/DesktopShell.tsx`
- `src/components/layout/Dock.tsx`

---

## 2. Einstellungen → Allgemein

### 2A. Textgröße

**Status:** `[x]`

- Neuer `uiStore` (Zustand + `persist`, Key `trion-ui`) speichert `fontSize: 'sm' | 'md' | 'lg' | 'xl'`
- Default: `'md'`
- `main.tsx` oder `App.tsx` liest `fontSize` und setzt CSS-Variable `--ui-font-scale` auf `<html>`
- Slider mit 4 Stufen + Label im Allgemein-Tab

**Betroffene Dateien (neu/geändert):**
- `src/state/uiStore.ts` (neu)
- `src/main.tsx`
- `src/features/settings/components/SettingsWindow.tsx`
- `src/features/settings/components/GeneralPanel.tsx` (neu)

### 2B. Hintergrundbild

**Status:** `[x]`

- `uiStore` bekommt `backgroundImage: string | null` (base64)
- File-Input im Allgemein-Tab, akzeptiert `image/*`
- `DesktopShell.tsx` liest Wert und setzt `background-image` inline auf dem Root-Container
- Glow-Effekte bleiben erhalten (liegen als `z-0`-Layer drüber)
- Button "Hintergrund zurücksetzen" setzt `backgroundImage` auf `null`
- Kein Backend-Call, keine API — rein lokal

**Betroffene Dateien:**
- `src/state/uiStore.ts`
- `src/app/shell/DesktopShell.tsx`
- `src/features/settings/components/GeneralPanel.tsx`

---

## 3. Fenster an Rändern skalieren (Resize Handles)

**Status:** `[x]`

- Resize-Handles an allen 8 Positionen: N, NE, E, SE, S, SW, W, NW
- Implementierung mit `onPointerDown/Move/Up` direkt im `WindowFrame` — kein Extra-Package
- Mindestgröße: 300 × 200 px
- `updateWindow` im `windowStore` ist bereits vorhanden und wird für `size` und `position` genutzt
- Handle-Zone: 6px breiter transparenter Rand, Cursor ändert sich je nach Richtung

**Betroffene Dateien:**
- `src/components/windows/WindowFrame.tsx`

---

## 4. Minimize & Maximize verdrahten

**Status:** `[x]`

- Minus-Button im Titelbalken: setzt `minimized: true` im `windowStore` → Fenster verschwindet
- Minimierte Fenster erscheinen als Pill-Buttons in einem Tray **oberhalb des Docks** (nicht im Dock selbst), je mit App-Icon und Fenster-Titel
- Klick auf einen Tray-Button stellt das Fenster wieder her (`minimized: false`) und fokussiert es
- Square-Button (Maximize2/Minimize2 Icon): togglet `maximized` — bei `true` nimmt das Fenster 100 % der Viewport-Fläche ein (minus Dock-Höhe von 120px)
- Doppelklick auf den Titelbalken togglet ebenfalls Maximize
- `windowStore` hat `minimized` und `maximized` bereits als Felder

**Betroffene Dateien:**
- `src/components/windows/WindowFrame.tsx`
- `src/components/windows/WindowManager.tsx` (Tray-Rendering)

---

## 5. Window Snap Zones

**Status:** `[x]`

- Fenster an den linken/rechten Bildschirmrand ziehen → snappt auf 50 % Breite
- Fenster in die obere Mitte ziehen → Vollbild (minus Dock)
- Snap-Indikator: halbtransparente Preview-Fläche erscheint beim Annähern an einen Randbereich
- Snap-Zone: letzte 40px vor dem jeweiligen Rand
- Snap wird beim `dragEnd` ausgewertet und über `updateWindow` in `position` + `size` gesetzt

**Betroffene Dateien:**
- `src/components/windows/WindowFrame.tsx`
- `src/components/windows/SnapPreview.tsx` (neu, eigene Komponente per Portal in `document.body`)

---

## 6. Akzentfarbe wählen (Erscheinungsbild-Tab)

**Status:** `[x]`

- `uiStore` bekommt `accentColor: string` (Hex-Wert, Default: `#eab308` — das aktuelle Gelb)
- `DesktopShell.tsx` setzt CSS-Variable `--color-primary` auf `document.documentElement` per `useEffect` — reagiert live auf Änderungen
- Farbpicker im Erscheinungsbild-Tab (natives `<input type="color">`)
- Ein paar Preset-Farben als Schnellauswahl (6 Stück: Gold, Blau, Lila, Grün, Rot, Weiß)
- Kein Backend, keine API

**Betroffene Dateien:**
- `src/state/uiStore.ts`
- `src/app/shell/DesktopShell.tsx`
- `src/features/settings/components/AppearancePanel.tsx` (neu)
- `src/features/settings/components/SettingsWindow.tsx`

---

## 7. Desktop-Uhr

**Status:** `[x]`

- Kleine Uhr oben rechts im Desktop (`top-4 right-6`, `z-50`, `pointer-events-none`)
- Rein Frontend: `setInterval` alle 10 Sekunden, zeigt `HH:MM` (Tabular-Nums) + deutsches Datum darunter (z.B. `Fr, 8. Mai`) in kleinerer Schrift
- Deutsche Wochentag- und Monats-Abkürzungen (Mo/Di/.../Jan/Feb/...)
- Kein Backend

**Betroffene Dateien:**
- `src/components/layout/DesktopClock.tsx` (neu)
- `src/app/shell/DesktopShell.tsx`

---

## 8. Desktop Right-Click Context Menu

**Status:** `[x]`

- Rechtsklick auf freien Desktop → Kontextmenü erscheint an Mausposition
- Einträge: Alle Apps aus `APP_REGISTRY` zum Öffnen + „Hintergrund zurücksetzen" (deaktiviert wenn kein Hintergrund gesetzt)
- Menü bleibt im Viewport (Auto-Reposition wenn zu nah am Rand)
- Schließt sich bei Klick außerhalb (Overlay-Layer mit `z-998`) oder `Escape`
- Framer Motion für Ein-/Ausblenden (Scale-Animation)
- Kein Backend

**Betroffene Dateien:**
- `src/components/layout/DesktopContextMenu.tsx` (neu)
- `src/app/shell/DesktopShell.tsx`

---

## 9. Dock Auto-Hide

**Status:** `[ ]`

- Option in Einstellungen (Allgemein oder Erscheinungsbild): `dockAutoHide: boolean` in `uiStore`
- Bei aktiv: Dock versteckt sich (`translateY(100%)`) nach 1,5s ohne Hover
- Erscheint sofort bei Hover am unteren Bildschirmrand (20px Trigger-Zone)
- Framer Motion für die Slide-Animation

**Betroffene Dateien:**
- `src/state/uiStore.ts`
- `src/components/layout/Dock.tsx`
- `src/features/settings/components/GeneralPanel.tsx`

---

## 10. Chat-Sidebar einklappbar (Collapse-Toggle)

**Status:** `[x]`

**Problem:**
- Im 420px Chat-Panel-Modus belegt die `ChatSessionSidebar` (`w-64` = 256px) ~60% der Breite
- Chat-Inhalt wird auf wenige Pixel zusammengequetscht — Text bricht zeichenweise um

**Lösung:**
- `ChatSessionSidebar` bekommt zwei Render-Varianten: `collapsed` (40px Strip) und `expanded` (volle 256px Breite)
- Chevron-Toggle (`ChevronLeft`/`ChevronRight`) zum manuellen Auf-/Zuklappen
- `ChatWindow` beobachtet die eigene Breite via `ResizeObserver`
- Auto-Collapse-Schwelle: 520px (darunter klappt automatisch ein)
- User-Override: sobald manuell getoggled wird, ist Auto-Verhalten für die Session deaktiviert
- Eingeklappte Sidebar zeigt: Toggle-Chevron, ➕ Neuer Chat, kleine Punkte pro Session (klickbar)

**Betroffene Dateien:**
- `src/features/chat/components/ChatSessionSidebar.tsx` (collapsed-Variante + Props)
- `src/features/chat/components/ChatWindow.tsx` (`ResizeObserver`, Toggle-Handler)

---

## 11. Dock- und Drag-Ghost-Icons in voller Größe

**Status:** `[x]`

**Problem:**
- Dock-Tiles und Drag-Overlay rendern Icons in `w-6 h-6` bzw. `w-7 h-7` innerhalb eines Glass/Border-Wrappers
- Custom-SVG-Icons aus Affinity wirken winzig, da sie nicht für so kleine Größen gedacht sind

**Lösung:**
- Glass/Border-Wrapper aus dem Dock-Button entfernen
- Icon mit `w-full h-full` direkt in den 56×56px Button gerendert (`rounded-2xl overflow-hidden`)
- Identisches Pattern für `DragOverlay` (Ghost-Icon beim Ziehen aus dem Launchpad)
- Hover-Animation (Scale 110% + Shadow) bleibt erhalten

**Betroffene Dateien:**
- `src/components/layout/Dock.tsx`
- `src/app/shell/DesktopShell.tsx` (DragOverlay)

---

## 12. MCP Installer — Tab-Layout

**Status:** 6-Tab-Struktur, Archiv-Upload (`zip`/`tar`/`tar.gz`/`tgz`), Toggle und
ownership-basiertes Uninstall `[x]`. GitHub-Install, Files-Backend und
Marketplace `[ ]`, Plugins-App initial `[x]`.

**Führende Doc:** [`docs/mcp/21-mcp-installer.md`](../../docs/mcp/21-mcp-installer.md) — Bundle-Contract,
Backend-Endpunkte, Runtime-Reload. Diese Implementation-Notiz beschreibt nur die WebUI-Seite.

**Problem:**
- Vorheriges Layout war Liste + Detail-Panel und vermischte Browse-, Manage- und Install-Flow
- Marktplatz-/Plugin-Suche bleibt aus dem Installer herausgelöst und soll als eigene App kommen

**Lösung:**
- `McpsWindow` ist eine Tab-Shell mit linker Sidebar und sechs Tabs
- `mcpsStore` hält `installerView: 'about' | 'all' | 'install' | 'uninstall' | 'files' | 'news'` plus `setInstallerView`
- Zusätzliche Store-Aktionen `toggleByName(name)` und `removeByName(name)` für die neuen Listen-Views (existierende `toggleSelected`/`removeSelected` brauchen nicht zwingend einen `selectedName`)
- TRION-Cube-Icon (`icon-mcp.svg`) als Sidebar-Header
- Aktiver Tab-Stil: dezentes `bg-white/8`, kein Gold/Settings-Look
- Destruktive Farbe wird erst innerhalb des `UninstallView` für Auswahl und Confirm-Actions genutzt

**Tab-Inhalte:**
- `AboutView` — Welcome-Screen, Supported-Sources-Card (GitHub + ZIP/TAR), Feature-Liste und Stats-Footer (Installed / Active / Offline).
- `AllView` — Filter-Chips (Installed / Online / Offline), Suche, Sort-Control und Tabelle mit Online/Offline-Toggle. Toggle ruft `POST /api/mcp/{name}/toggle`, Refresh kommt über `GET /api/mcp/list`.
- `InstallView` — Split-Layout: ZIP/TAR-Drop-Zone links, GitHub-Card rechts. Backend akzeptiert jetzt dieselben Archivformate wie die UI. GitHub hat ein `soon`-Badge und disabled Install-Button. Footer-Optionen (Auto-enable / Health-check / Pin to dock) sind lokale UI-States.
- `UninstallView` — Multi-Select-Tabelle mit Header-Checkbox, Single-Trash und Batch-Footer. Confirm via `ConfirmRemoveModal`; Confirm ruft `removeByName(name)` → `DELETE /api/mcp/{name}`.
- `FilesView` — UI-only Dateiliste für `~/.trion/mcp` mit `MOCK_FILES`, Suche sowie Upload/New-Buttons ohne Backend-Wiring.
- `NewsView` — statischer Changelog aus lokaler `CHANGELOG`-Konstante.
- `McpSettingsWindow` — generischer Host-Settings-Editor für MCPs mit `ui.settings.enabled`, backed by `GET /api/mcp/{name}/details` und `PUT /api/mcp/{name}/config`.
- `mcpHostApps.ts` — leitet dynamische Launchpad-/Dock-Apps aus `ui.launchpad` und `ui.settings` ab.
- Der Save-Pfad validiert `mcp.json` und `config.json` jetzt über denselben Backend-Manifest-Contract wie der Upload; `stdio`-Bundles behalten dabei ihren installer-owned `cwd`/`.venv`-Kontext.

**App-Registry-Änderung:**
- Label `MCP` → `MCP Installer`
- Window-Titel `MCP` → `MCP Installer`
- Default-Größe `1100×720` → `880×600`

**Betroffene Dateien:**
- `src/lib/contracts/appRegistry.ts` (Label, Titel, Default-Größe)
- `src/features/mcps/state/mcpsStore.ts` (`installerView`, `setInstallerView`, `toggleByName`, `removeByName`)
- `src/features/mcps/components/McpsWindow.tsx` (Tab-Shell)
- `src/features/mcps/components/McpsSidebar.tsx` (6-Tab-Navigation + TRION-Cube-Header)
- `src/features/mcps/components/views/AboutView.tsx` (neu)
- `src/features/mcps/components/views/AllView.tsx` (neu)
- `src/features/mcps/components/views/InstallView.tsx` (neu)
- `src/features/mcps/components/views/UninstallView.tsx` (neu)
- `src/features/mcps/components/views/FilesView.tsx` (neu, UI-only)
- `src/features/mcps/components/views/NewsView.tsx` (neu, statisch)
- `src/features/mcps/components/views/ConfirmRemoveModal.tsx` (shared Confirm-Dialog)
- `src/features/mcps/components/McpSettingsWindow.tsx` (generische MCP-Settings)
- `src/lib/contracts/mcpHostApps.ts` (dynamische Host-App-Ableitung)

**Begleitender Backend-Fix (nicht WebUI):**
- `mcp/installer_install_routes.py` — `Request | None` Parameter-Type wurde von FastAPI als Pydantic-Field interpretiert und brach den Container-Start. Behoben durch `request: Request` (ohne Optional, FastAPI injectet immer) plus `response_model=None` am Decorator.

---

## 13. Einstellungen — OSX-Style Redesign

**Status:** `[x]` — rein visueller Refactor, alle Endpunkte und Stores unverändert.

**Problem:**
- Settings-App nutzte den älteren Stil (gold-getönte Active-Tabs, große Custom-SVG-Icons in der Sidebar, flache Section-Header ohne Card-Wrap), während der MCP Installer schon im ruhigen System-Settings-Look lebt
- Inkonsistente Optik machte den Eindruck zweier verschiedener Apps statt einer Familie

**Lösung:**
- `SettingsWindow.tsx` neuer Sidebar-Stil: Icon-Card-Header („Einstellungen / v 1.0 · TRION"), 5 Tabs mit kleinen 20×20 farbigen Icon-Quadraten im macOS-System-Settings-Stil (Allgemein grau, KI & Verhalten lila, Erscheinungsbild rosa, Modelle blau, API amber), Lucide-Glyph innen. Active-Tab als dezente `bg-white/8`-Pille — Gold raus aus der Nav.
- Einheitliches Content-Header-Pattern in allen Panels: kleines `uppercase tracking-[0.18em]` Eyebrow + großer `text-[22px] font-semibold` Titel + muted Subtitle
- Sections jetzt als `rounded-2xl border-white/6 bg-white/[0.02]` Cards statt nackte Headlines
- Content-Padding `px-8 py-7` für mehr Atem
- Window-Default-Size `640×460` → `800×560`
- `KiVerhaltenPanel.tsx` ersetzt den alten Ein-Panel-Editor durch eine macOS-List-Navigation mit 7 Sub-Views unter `views/ki/`: Persona, Arbeitsmodus, Planungstiefe, Warteverhalten, Sicherheitsebene, Fehlerverhalten, Schleifenerkennung
- `PersonaPanel.tsx` innerhalb von `views/ki/` nutzt weiter `personaApi.ts` + `personaEditor.ts`; die Persona bleibt damit der einzige Teil des Tabs mit echtem Backend-Wiring
- `autonomyApi.ts` + `useAutonomyProfile.ts` verdrahten Arbeitsmodus, Planungstiefe, Warteverhalten, Sicherheitsebene, Fehlerverhalten und Schleifenerkennung jetzt live an `GET/POST /api/settings/autonomy/profile`
- Der Backend-Contract bleibt bewusst UI-nah; die Admin-API mappt diese 6 Felder serverseitig auf bestehende Runtime-Keys wie `TASK_LOOP_MAX_STEPS`, `SEQUENTIAL_TIMEOUT_S`, `TASK_LOOP_MAX_RETRIES_PER_STEP` und Query-Budget-Defaults
- `personaEditor.ts` parst bestehende Persona-Dateien und baut daraus wieder die kanonische `/personas/*.txt`-Struktur für `PUT /api/personas/content/{name}`
- Persona-Dateien werden zur Laufzeit aus `/personas/*.txt` gelesen; Speichern/Umschalten braucht keinen Rebuild

**File-Splits zur Einhaltung der 200-Zeilen-Regel:**
- `RoleCard.tsx` (134 Z.) ausgelagert aus `ProviderSettingsPanel.tsx` — kapselt RoleCard + SelectField + MiniCard + SourceBadge
- `providerSettingsHelpers.ts` (127 Z.) — alle pure helpers (`buildRoleState`, `dedupeModelNames`, `visibleModelsForProvider`, `errorMessage`) + Constants + Types
- `ApiKeysTable.tsx` (63 Z.) ausgelagert aus `ApiKeysPanel.tsx`
- `KiVerhaltenPanel.tsx` (174 Z.) hält Navigation + Host-Status fuer das neue Autonomy-Profil
- `useAutonomyProfile.ts` (76 Z.) kapselt Laden, optimistisches Speichern und Fehlerstatus fuer `KI & Verhalten`
- `autonomyApi.ts` (48 Z.) kapselt den UI-nahen Host-Contract `/api/settings/autonomy/profile`
- `views/ki/*.tsx` splitten die 7 Detailansichten sauber unter 200 Zeilen
- `personaApi.ts` (43 Z.) + `personaEditor.ts` (153 Z.) bleiben der Backend-/Parsing-Pfad für die Persona

**Was nicht angefasst wurde:** alle API-Endpunkte, alle Stores, alle Persistenz, alle Backend-Pfade — rein visueller Refactor. Affinity-Icons im Launchpad und Dock bleiben unverändert; die kleinen farbigen Tab-Quadrate in der Settings-Sidebar nutzen Lucide-Glyphen, damit die großen Affinity-Icons nicht in Mini-Größe gestaucht werden.

**Betroffene Dateien:**
- `src/lib/contracts/appRegistry.ts` (Settings-Default-Size 640×460 → 800×560)
- `src/features/settings/components/SettingsWindow.tsx`
- `src/features/settings/components/GeneralPanel.tsx`
- `src/features/settings/components/AppearancePanel.tsx`
- `src/features/settings/components/ProviderSettingsPanel.tsx`
- `src/features/settings/components/RoleCard.tsx` (neu)
- `src/features/settings/components/ApiKeysPanel.tsx`
- `src/features/settings/components/ApiKeysTable.tsx` (neu)
- `src/features/settings/components/KiVerhaltenPanel.tsx`
- `src/features/settings/components/views/ki/*`
- `src/features/settings/providerSettingsHelpers.ts` (neu)

---

## 14. Chat Pipeline Sichtbarkeit — Visible Thinking als Live-Trace

**Status:** `[x]` — rein Frontend-Rendering. Chat Event Contract und Backend-Stream
unveraendert.

**Fuehrende Doc fuer den Event-Contract:** [`docs/contracts/10-chat-event-contract.md`](../../docs/contracts/10-chat-event-contract.md).

**Problem:**
- Waehrend des Streams sah der User nur drei pulsierende Dots und winzige Event-Chip-Labels ohne Inhalt — der eigentliche Pipeline-Fortschritt war nicht ablesbar.
- Die alte `PipelineTraceCard` war eine Demo-artige Card mit Sky-Tint, Section-Headern (Classifier/Plan/Verifier), Pills fuer jedes Metadatum und Step-Boxen — wirkte ueberladen und blaehte jede Antwort auf.
- Das outer `motion.div layout` auf der MessageBubble erzwang beim Aufklappen der Card eine Spring-Animation ueber die gesamte Bubble-Hoehe und fuehrte zu spuerbarem Lag.
- `TaskLoopStatusCard` rendete bei jedem Stream ohne Aktionspflicht.

**Loesung:**
- Neuer `LiveStageStrip.tsx` in der Bubble: ersetzt waehrend `isStreaming && content === ''` die drei Loading-Dots durch eine einzeilige animierte `STAGE -> detail`-Anzeige (Classifying / Planning / Tool / Verifying / Task loop) auf Basis des jeweils letzten Pipeline-Events aus `msg.events`.
- Neuer `ThinkingTrace.tsx` als Ersatz fuer `PipelineTraceCard`: natives `<details>`, default zu, Header `> Thinking` mit subtilem Pulse-Dot waehrend Stream. Aufgeklappt zeigt es einen flachen chronologischen Log aus kontrollierten oeffentlichen Status-, Kategorie-, Boolean- und Count-Feldern; freie Planungs- und Verifier-Gruende bleiben intern.
- Hueller-Look "eingestanzt": `bg-black/25`, hauchduenner Border `border-white/5`, GPU-billige Doppel-`inset`-Shadow (oben dunkler Groove, unten Hairline-Highlight). Kein blur, kein backdrop-filter.
- `task_loop_state` wird ueber kontrollierte State-/Index-/Count-Felder dargestellt; Tool-Events und React-Keys benoetigen keine oeffentlichen internen Step-IDs.
- `TaskLoopStatusCard` rendert jetzt nur noch wenn der letzte `task_loop_state` in `waiting/blocked/cancelled` ist oder ein `task_loop_waiting`-Event vorliegt (actionable states). Sonst weg.
- Performance-Cleanup auf `MessageBubble`: `layout` Prop entfernt, Spring + Scale durch kurzes `opacity/y`-Fade ersetzt, `useChatStore` jetzt mit Selektoren statt vollem Store-Destructure — kein Komplett-Rerender pro eingehendem Event mehr.
- Aelterer Chip-Streifen ueber der Bubble (PipelineEventChip-Row) und die ungenutzten Lucide-Icons entfernt.

**Betroffene Dateien:**
- `src/features/chat/components/LiveStageStrip.tsx` (neu)
- `src/features/chat/components/ThinkingTrace.tsx` (neu)
- `src/features/chat/components/PipelineTraceCard.tsx` (geloescht)
- `src/features/chat/components/ChatMessageList.tsx`

---

## 15. Memory App — Browser, Suche, Vergessen, Privacy-Badge (Phase 1)

**Status:** `[x]` — Phase 1 (App fuer Memory-Inhalt). Phase 2 (Settings-Tab
unter `KI & Verhalten > Memory` fuer Policy/Verhalten) ist noch offen.

**Fuehrende Doc fuer Memory-Policy:** [`docs/memory-grounding/15-conversation-metadata-context-scopes.md`](../../docs/memory-grounding/15-conversation-metadata-context-scopes.md).
**Fuehrende Doc fuer Memory-Hygiene:** [`docs/memory-grounding/30-traumzustand-memory-hygiene.md`](../../docs/memory-grounding/30-traumzustand-memory-hygiene.md).
**Endpunkt-Tabelle:** [`docs/adapters/17-webui-api-endpoints.md`](../../docs/adapters/17-webui-api-endpoints.md) Abschnitt Memory App.

**Problem:**
- Memory war fuer den User bislang eine Blackbox — was hat TRION sich gemerkt? Wann? Pro Conversation?
- Keine UI fuer "vergessen", obwohl Vertrauensbasis
- Keine Sichtbarkeit der Conversation-Privacy/Scope-Modi
- Risiko: ohne Browser-Sicht entstehen Halluzinations-Schleifen, weil Memory wirkt, ohne dass der User sie pruefen kann (Zusammenhang zu docs/30)

**Loesung:**
- Eigene App `Memory` als Launchpad-Eintrag, Sidebar-Layout im OSX-Style (Eyebrow + grosser Titel + Subtitle, Cards `rounded-2xl border-white/6 bg-white/[0.02]`, kein Gold-Akzent)
- Drei Views: `Zuletzt` (juengste Eintraege), `Suchen` (drei Modi `fts`/`semantic`/`graph` getrennt, jeweils gegen den passenden MCP-Tool-Pfad), `Unterhaltungen` (Liste + Drill-In pro Conversation)
- `Vergessen`-Action pro Eintrag mit Confirm-Modal vor `DELETE /api/memory/{id}`
- `PrivacyBadge` pro Conversation aus `GET /api/memory/conversations/{id}/policy` (read-only Anzeige; editieren kommt in Phase 2)
- Stabile WebUI-Vertraege ueber neuen Router `adapters/admin-api/memory_routes.py`, der intern die SQL-Memory-MCP-Tools ueber `mcp/client.py::call_tool` aufruft — keine generische `tools/call`-Proxy-Nutzung in der WebUI

**Anti-Drift-Linie:**
- Router enthaelt keine hartcodierten Memory-Tool-Listen (docs/36 Regel 2)
- Anti-Drift-Test `tests/test_memory_routes.py::test_memory_routes_no_hardcoded_tool_list` blockt Regressionen
- Trennung zur aelteren `trion_memory_routes.py` ist im Header dokumentiert (anderer Scope: Home-/Note-Pfad an `container_commander`)

**Betroffene Dateien:**
- `adapters/admin-api/memory_routes.py` (neu)
- `adapters/admin-api/main.py` (neuer Router registriert als `memory_app_router`)
- `tests/test_memory_routes.py` (neu, 17 Tests inkl. Anti-Drift-Guard)
- `adapters/webui/src/features/memory/contracts.ts` (neu)
- `adapters/webui/src/features/memory/api.ts` (neu)
- `adapters/webui/src/features/memory/state/memoryStore.ts` (neu)
- `adapters/webui/src/features/memory/components/MemoryWindow.tsx` (neu)
- `adapters/webui/src/features/memory/components/MemorySidebar.tsx` (neu)
- `adapters/webui/src/features/memory/components/MemoryEntryItem.tsx` (neu)
- `adapters/webui/src/features/memory/components/PrivacyBadge.tsx` (neu)
- `adapters/webui/src/features/memory/components/ForgetConfirmModal.tsx` (neu)
- `adapters/webui/src/features/memory/components/views/RecentView.tsx` (neu)
- `adapters/webui/src/features/memory/components/views/SearchView.tsx` (neu)
- `adapters/webui/src/features/memory/components/views/ConversationsView.tsx` (neu)
- `adapters/webui/src/lib/contracts/appRegistry.ts` (Memory-App-Eintrag)
- `adapters/webui/src/components/icons/AppIcon.tsx` (Memory-Icon-Mapping)
- `adapters/webui/src/components/windows/WindowManager.tsx` (Routing fuer `appId === 'memory'`)
- `docs/memory-grounding/15-conversation-metadata-context-scopes.md` (Status-Update WebUI)
- `docs/adapters/17-webui-api-endpoints.md` (Abschnitt Memory App)

**Bewusst offen fuer Phase 2 und spaeter:**
- Settings-Tab `Settings > KI & Verhalten > Memory` mit den fuenf Pflicht-Togglen (`memory_mode`, `do_not_remember`, `allow_long_term_write`, `allow_global_memory_read`, `max_memory_hits`)
- Facts-Tab — braucht zuerst sauberen Browse-Contract (kein `memory_fact_load(all)` heute)
- Maintenance-Tab (orphans, dupes, embedding-backfill) hinter "Erweitert"-Toggle
- Chat → Memory Deep-Link (greift in Chat-Event-Contract ein, siehe docs/10)
- Edit von strukturierten Facts (nur wenn Trennung curated vs auto-extracted sauber, vgl. docs/30 Z.131-136)

---

## 16. Memory Settings — Erinnerungsverhalten (Phase 2)

**Status:** `[x]` — Settings-Tab fuer Memory-Default-Verhalten ist umgesetzt.

**Fuehrende Doc:** [`docs/memory-grounding/15-conversation-metadata-context-scopes.md`](../../docs/memory-grounding/15-conversation-metadata-context-scopes.md).
**Backend-Endpunkt:** [`docs/adapters/17-webui-api-endpoints.md`](../../docs/adapters/17-webui-api-endpoints.md) Memory-Defaults-Eintrag.

**Problem:**
- Memory-Defaults fuer neue Conversations waren hartcodiert in `core/conversation_meta/defaults.py` (`memory_mode=global_enabled`, `do_not_remember=false`)
- Kein User-Steuerpunkt: man konnte TRION nicht global anweisen, sich nichts zu merken oder Memory auf den aktuellen Chat zu beschraenken
- `max_memory_hits` ebenfalls hartcodiert (5) in `core/self_context/builder.py`
- Risiko bei Mehrfach-Toggles: zwei Wahrheiten fuer ein Konzept, wenn allow_long_term_write parallel persistiert wird (Doc 13-Verstoss)

**Loesung:**
- Settings-Tab `KI & Verhalten > Memory` mit Apple-aehnlichem UX-Schnitt:
  - eine zentrale Frage oben: "Darf TRION sich Dinge merken?"
  - drei klar formulierte Optionen statt fuenf Fachbegriff-Toggles:
    - **Ja, dauerhaft** (Standard) -> `memory_mode=global_enabled, do_not_remember=false`
    - **Nur diese Unterhaltung** -> `memory_mode=conversation_only, do_not_remember=false`
    - **Nein, nichts** -> `memory_mode=disabled, do_not_remember=true`
  - "Erweitert"-Bereich, default zugeklappt: `max_memory_hits`-Slider plus abgeleitete read-only Anzeige
- Neuer Backend-Router `adapters/admin-api/memory_defaults_routes.py` mit `GET/POST /api/settings/memory/defaults`
- Einzige Quelle pro Konzept: persistiert werden nur `memory_mode`, `do_not_remember`, `max_memory_hits`. `allow_long_term_write` und `allow_global_memory_read` werden im Backend aus diesen Werten abgeleitet (gleiche Logik wie `core/conversation_meta/policy.py::build_effective_policy`)
- `core/conversation_meta/defaults.py::build_default_conversation_meta()` liest jetzt die persistenten Settings mit Hardcoded-Fallback — bestehende `tests/test_conversation_meta.py` laufen weiter

**Anti-Drift-Linie:**
- Test `tests/test_memory_defaults_routes.py::test_no_persistence_of_derived_fields` blockt Regressionen, bei denen abgeleitete Felder parallel persistiert werden
- Pydantic `extra="forbid"` blockt unbekannte Felder im POST-Body
- `MemoryDefaultsUpdate` akzeptiert keine `allow_long_term_write`-Eingabe

**Betroffene Dateien:**
- `adapters/admin-api/memory_defaults_routes.py` (neu)
- `adapters/admin-api/main.py` (Router registriert)
- `core/conversation_meta/defaults.py` (Settings-Reader mit Fallback)
- `core/self_context/builder.py` (`max_memory_hits` aus Settings)
- `tests/test_memory_defaults_routes.py` (neu, 13 Tests inkl. Anti-Drift-Guard)
- `adapters/webui/src/features/settings/memoryDefaultsApi.ts` (neu)
- `adapters/webui/src/features/settings/useMemoryDefaults.ts` (neu)
- `adapters/webui/src/features/settings/components/views/ki/MemoryPanel.tsx` (neu)
- `adapters/webui/src/features/settings/components/KiVerhaltenPanel.tsx` (achter Eintrag "Erinnerung" mit Brain-Icon)
- `docs/memory-grounding/15-conversation-metadata-context-scopes.md` (Status-Update)
- `docs/adapters/17-webui-api-endpoints.md` (Endpoint-Tabelle)

---

## Hinweise

- Alle neuen Store-Felder kommen in `src/state/uiStore.ts` (wird neu angelegt).
- Kein API-Call, kein Backend-Kontakt für alle Punkte hier.
- Max. 200 Zeilen pro Datei einhalten — bei `WindowFrame.tsx` ggf. ResizeHandle in eigene Datei auslagern.
- Contracts vor Logik: falls neue Event-Typen oder Typen entstehen, zuerst in `src/lib/contracts/` definieren.
