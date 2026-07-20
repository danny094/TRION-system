---
title: WebUI Design-Regeln
tags: [rules, webui, frontend, design, architecture, trion]
created: 2026-05-06
---

# WebUI Design-Regeln

← [[TRION|Zurück zur Übersicht]]

> Diese Regeln verhindern, dass die TRION WebUI wieder zu einer großen, schwer wartbaren Jarvis-Oberfläche wird.
> Die WebUI ist keine normale Webseite. Sie ist die Shell von TRION.

---

## Grundsatz

Die TRION WebUI ist eine lokale AI-OS-Shell.

Sie soll sich anfühlen wie:

- ein leichtes Betriebssystem
- ein App-Launcher
- ein Kontrollzentrum
- ein sicherer Workspace
- eine lokale AI-Umgebung

Sie ist **nicht** nur eine Chat-Seite.

---

## Empfohlener Stack

Für WebUI v2:

```text
Vite
React
TypeScript
Tailwind CSS
shadcn/ui
Radix UI
Zustand
dnd-kit
Framer Motion
xterm.js
Monaco Editor
```

---

## Datei-Regeln

- **Max 200 Zeilen pro Datei**
- Wird eine Datei größer, wird sie aufgeteilt
- Jede Datei hat genau eine Aufgabe
- Keine UI-Komponente enthält API-, Sicherheits- und Renderlogik gleichzeitig
- Einstiegspunkte enthalten keine Geschäftslogik
- Keine `.old`, `.bak`, `.broken`, `.tmp` Dateien
- Keine zweite WebUI-Wahrheit neben dem Backend

---

## Ordnerstruktur

Empfohlener Pfad:

```text
adapters/webui-next/
```

Empfohlene Struktur:

```text
adapters/webui-next/
├─ src/
│  ├─ app/
│  │  ├─ shell/
│  │  ├─ providers/
│  │  └─ router/
│  ├─ components/
│  │  ├─ ui/
│  │  ├─ layout/
│  │  ├─ windows/
│  │  ├─ panels/
│  │  └─ icons/
│  ├─ features/
│  │  ├─ chat/
│  │  ├─ terminal/
│  │  ├─ vault/
│  │  ├─ settings/
│  │  ├─ memory/
│  │  ├─ runtime/
│  │  ├─ containers/
│  │  ├─ skills/
│  │  └─ plugins/
│  ├─ lib/
│  │  ├─ api/
│  │  ├─ events/
│  │  ├─ stream/
│  │  ├─ contracts/
│  │  └─ utils/
│  ├─ state/
│  └─ main.tsx
├─ public/
├─ package.json
├─ vite.config.ts
├─ tsconfig.json
└─ Dockerfile
```

---

## Import-Regeln

```text
components/ui/       ← importiert keine Features
components/layout/   ← importiert ui/
components/windows/  ← importiert ui/ und layout/
features/            ← importiert components/, lib/, state/
lib/                 ← importiert keine UI-Komponenten
state/               ← importiert contracts/, aber keine Komponenten
app/                 ← verdrahtet Shell, Provider und Features
```

**Pfeile zeigen erlaubte Import-Richtung. Keine Kreise.**

---

## Komponenten-Regeln

Eine Komponente darf genau eine Hauptaufgabe haben.

Erlaubt:

- Anzeige
- Layout
- Interaktion
- kleines lokales UI-Verhalten

Nicht erlaubt:

- API-Calls direkt in tiefen Komponenten
- Event-Stream direkt in UI-Komponenten parsen
- Sicherheitsentscheidungen in Komponenten
- Runtime-Zustände erfinden
- Backend-Status optimistisch als Erfolg anzeigen

---

## Feature-Regeln

Jedes größere WebUI-Modul ist ein eigenes Feature.

Beispiele:

```text
features/chat/
features/terminal/
features/vault/
features/settings/
features/runtime/
features/plugins/
```

Jedes Feature darf haben:

```text
components/
hooks/
state/
api.ts
contracts.ts
index.ts
```

Beispiel:

```text
features/chat/
├─ components/
│  ├─ ChatWindow.tsx
│  ├─ ChatInput.tsx
│  ├─ ChatMessageList.tsx
│  └─ ToolEventCard.tsx
├─ hooks/
│  └─ useChatStream.ts
├─ state/
│  └─ chatStore.ts
├─ api.ts
├─ contracts.ts
└─ index.ts
```

---

## Contract-Regeln

- Jeder API-/Event-Typ wird zuerst als Contract definiert
- Keine frei geratenen Objekte in Komponenten
- Keine Stringly-Typed Event-Logik quer durch die UI
- Eventtypen werden zentral definiert
- UI rendert nur bekannte Events sauber
- Unbekannte Events werden neutral dargestellt, nicht interpretiert

Beispiele:

```text
lib/contracts/chatEvents.ts
lib/contracts/runtime.ts
lib/contracts/vault.ts
lib/contracts/settings.ts
```

---

## Event-Regeln

Der Event Contract ist führend.

Die WebUI darf Events anzeigen, aber nicht uminterpretieren.

Wichtige Events:

```text
message
thinking
tool_call
tool_result
control_decision
approval_required
done
error
blocked
rejected
```

Regeln:

- `blocked` ist nicht dasselbe wie `error`
- `rejected` ist nicht dasselbe wie `blocked`
- `approval_required` darf nicht als Erfolg gerendert werden
- `tool_call` ohne `tool_result` ist kein abgeschlossener Erfolg
- `done` beendet einen Lauf sichtbar
- Fehler müssen sichtbar und unterscheidbar bleiben

---

## State-Regeln

State wird klar getrennt.

```text
Server-State:
- laufende Container
- Vault Status
- verfügbare Skills
- Chat Events
- Runtime Health
- aktive Sessions

UI-State:
- offene Fenster
- Fensterposition
- aktives Panel
- Sidebar offen/geschlossen
- Suchbegriff
- Theme
- Launcher-Sortierung

Session-State:
- aktueller Chat
- aktive Verbindung
- Stream Status
- ausgewählte Runtime

Plugin-State:
- registrierte Apps
- Berechtigungen
- sichtbare Plugin-Fenster
```

Kein State-Mix in einer Monster-Datei.

---

## Store-Regeln

Empfohlen:

```text
Zustand
```

Regeln:

- ein Store pro klarer Domäne
- keine globalen Alleskönner-Stores
- kein Store darf Backend-Wahrheiten erfinden
- persistenter UI-State muss klar markiert sein
- Runtime-State kommt vom Backend/Event-Stream

Beispiele:

```text
state/shellStore.ts
state/windowStore.ts
features/chat/state/chatStore.ts
features/runtime/state/runtimeStore.ts
features/plugins/state/pluginStore.ts
```

---

## API-Regeln

- API-Calls liegen nicht in Komponenten
- API-Calls liegen in `lib/api/` oder im jeweiligen Feature
- Jede API-Funktion gibt typisierte Daten zurück
- Fehler werden normalisiert
- Keine Komponenten bauen URLs per String zusammen
- Keine Secrets im Frontend
- Keine API-Keys im localStorage

Beispiel:

```text
lib/api/client.ts
features/vault/api.ts
features/settings/api.ts
features/runtime/api.ts
```

---

## Stream-Regeln

- NDJSON/Event-Streams werden zentral verarbeitet
- Stream Parser liegt nicht in der Chat-Komponente
- Stream Events werden typisiert
- Stream Fehler werden sichtbar gemacht
- Reconnect-Logik liegt außerhalb der UI-Komponenten
- UI zeigt den echten Stream-Zustand

Zustände:

```text
idle
connecting
streaming
done
error
cancelled
blocked
rejected
```

---

## Shell-Regeln

Die Shell ist die WebUI-Grundstruktur.

Sie enthält:

- App Launcher
- Dock oder Sidebar
- Window Manager
- Command Palette
- Notification Center
- Status Bar

Die Shell entscheidet nicht über Runtime-Wahrheiten.

Sie organisiert nur UI und Navigation.

---

## App-Launcher-Regeln

Der App-Launcher zeigt registrierte Apps.

Jede App braucht:

```text
id
name
icon
description
category
permissions
entry
defaultSize
canPin
canOpenMultiple
```

Regeln:

- Apps werden aus einer Registry geladen
- keine hardcodierte App-Logik im Launcher
- App-Positionen dürfen gespeichert werden
- Drag & Drop verändert nur UI-State
- App-Badges müssen aus echtem State kommen
- keine Fake-Badges

---

## Drag-&-Drop-Regeln

Für verschiebbare Apps:

Empfohlen:

```text
dnd-kit
```

Regeln:

- Drag verändert nur Layout-State
- App-Funktionalität bleibt unverändert
- Positionen werden separat gespeichert
- Reset Layout muss möglich sein
- Drag darf keine Runtime-Aktion auslösen
- Drag-Modus und Klick-Modus müssen klar getrennt sein

---

## Window-Manager-Regeln

Wenn Apps als Fenster geöffnet werden:

Jedes Fenster hat:

```text
windowId
appId
title
position
size
zIndex
minimized
maximized
focused
```

Regeln:

- Fenster-State liegt zentral
- App-Inhalt liegt im jeweiligen Feature
- Fensterrahmen ist Shell-Logik
- App-Logik ist Feature-Logik
- Fenster dürfen keine Runtime-Aktionen versteckt auslösen

---

## Design-Regeln

Die WebUI soll wirken wie:

- ruhig
- hochwertig
- klar
- lokal
- sicher
- technisch, aber nicht kalt
- AI-OS statt Admin-Panel

Vermeiden:

- zu viele Linien
- zu viele Tabellen
- zu viele gleich schwere Elemente
- grelle Farben ohne Bedeutung
- überladene Dashboards
- zufällige Icons
- Admin-Panel-Look

---

## Farbsystem

Farben haben Bedeutung.

Beispiele:

```text
Blau   → Chat / Kommunikation
Grün   → Memory / Persistenz / Gesund
Orange → Tools / Aktion / Wartung
Lila   → Logs / Analyse / System
Rot    → Fehler / Block / Risiko
Gelb   → Warnung / Approval / Aufmerksamkeit
```

Regeln:

- Farbe niemals nur dekorativ einsetzen
- Risiko und Erfolg müssen visuell unterscheidbar sein
- Warnung darf nicht wie Fehler aussehen
- Pending darf nicht wie Erfolg aussehen

---

## Icon-Regeln

- Icons kommen zentral aus einer Icon-Schicht
- Keine zufälligen Icon-Sets mischen
- Icons brauchen klare Bedeutung
- Kritische Aktionen bekommen eindeutige Icons
- Icons ersetzen keine Labels bei wichtigen Aktionen

Empfohlen:

```text
lucide-react
```

---

## Motion-Regeln

Animationen sind erlaubt, aber kontrolliert.

Empfohlen:

```text
Framer Motion
```

Erlaubt:

- Hover
- Fenster öffnen/schließen
- App verschieben
- Panel ein-/ausklappen
- kleine Statusübergänge

Nicht erlaubt:

- dauernd blinkende Elemente
- Animationen, die Status verschleiern
- Spielerei bei Fehlern oder Sicherheitsereignissen
- langsame Animationen im Arbeitsfluss

Grundsatz:

```text
Motion unterstützt Orientierung.
Motion ist kein Selbstzweck.
```

---

## Feedback-Regeln

Jede Nutzeraktion braucht klares Feedback.

Beispiele:

```text
Klick
Lädt
Erfolg
Fehler
Blockiert
Wartet auf Approval
Keine Verbindung
Keine Berechtigung
```

Nicht erlaubt:

- Button klickt, aber nichts passiert sichtbar
- Erfolg anzeigen ohne Backend-Bestätigung
- Fehler nur in der Konsole
- Ladezustand ohne Ende
- Approval als normalen Ladezustand tarnen

---

## Sicherheits-Regeln

Die WebUI darf Sicherheit niemals „hübsch verstecken“.

Pflicht:

- Approval sichtbar anzeigen
- Blocked sichtbar anzeigen
- Rejected sichtbar anzeigen
- gefährliche Aktionen klar markieren
- destructive actions bestätigen lassen
- keine Secrets anzeigen, außer explizit angefordert
- keine API-Keys im Frontend speichern
- keine echten Secrets in Logs rendern

---

## Vault-Regeln

- Vault ist ein eigenes Feature
- Vault zeigt Status getrennt von Secrets
- Secrets werden niemals dauerhaft im UI-State gespeichert
- Passwörter/API-Keys werden nur temporär angezeigt
- Kopieren ist erlaubt, aber sichtbar
- Reveal braucht bewusste Aktion
- Vault-Lock muss klar sichtbar sein

---

## Terminal-Regeln

Terminal ist mächtig und riskant.

Regeln:

- Terminal ist eine eigene App
- Terminal zeigt klar, welcher Container aktiv ist
- kein Terminal ohne Kontext
- keine versteckte Ausführung
- Copy/Paste bei gefährlichen Befehlen vorsichtig behandeln
- Terminal-Ausgaben dürfen UI nicht blockieren
- Verbindungsstatus sichtbar anzeigen

---

## Logs-Regeln

Logs sind Diagnose, nicht Dekoration.

Regeln:

- Logs filterbar machen
- Log-Level unterscheiden
- Fehler sichtbar hervorheben
- lange Logs virtualisieren
- Logs nicht ungefiltert in normale UI kippen
- sensible Werte maskieren

Log-Level:

```text
debug
info
warning
error
critical
```

---

## Plugin-Regeln

Plugins dürfen nicht frei in die WebUI greifen.

Jedes Plugin braucht:

```text
manifest.json
id
name
version
entry
permissions
routes
events
```

Regeln:

- keine Plugin-Ausführung ohne Manifest
- keine stillen Berechtigungen
- Plugin-UI wird isoliert
- Plugin darf nur definierte Host-API nutzen
- Plugin darf keine globalen Stores direkt verändern
- Plugin darf keine Secrets lesen ohne Berechtigung
- Plugin-Fehler dürfen die Shell nicht crashen

---

## Performance-Regeln

Die WebUI muss schnell bleiben.

Regeln:

- große Listen virtualisieren
- Logs nicht komplett rendern
- Stream-Rendering drosseln
- unnötige Re-Renders vermeiden
- Icons/Assets lokal bündeln
- keine unnötigen CDN-Abhängigkeiten
- Build-Größe beobachten

Ziel:

```text
Start schnell
Chat schnell
Terminal direkt
Keine UI-Freezes bei Logs oder Streams
```

---

## Accessibility-Regeln

Auch eine lokale Dev-WebUI braucht Bedienbarkeit.

Pflicht:

- Tastaturbedienung
- sichtbarer Fokus
- lesbare Kontraste
- Buttons mit Labels
- Dialoge mit Escape schließbar
- kritische Aktionen nicht nur über Farbe erkennbar
- Command Palette per Tastatur erreichbar

---

## Responsive-Regeln

Die WebUI ist primär Desktop-first.

Aber sie darf auf kleineren Screens nicht brechen.

Priorität:

```text
1. Desktop
2. Laptop
3. Tablet
4. Mobile nur eingeschränkt
```

Regeln:

- Desktop ist Hauptziel
- Mobile darf reduziert sein
- Terminal und Logs dürfen Mobile-Limits haben
- Shell muss auf kleinen Screens kontrolliert zusammenklappen

---

## Fehler-Regeln

Fehler sind Teil der UI.

Fehler müssen zeigen:

```text
Was ist passiert?
Wo ist es passiert?
Kann der Nutzer etwas tun?
Ist es ein UI-, API-, Runtime- oder Safety-Fehler?
```

Nicht erlaubt:

- generisches „Something went wrong“
- Fehler nur in DevTools
- Error Toast ohne Kontext
- Retry ohne sichtbaren Status

---

## Empty-State-Regeln

Leere Zustände sind bewusst gestaltet.

Beispiele:

```text
Keine Chats
Keine Container
Keine Logs
Keine Skills
Vault gesperrt
Keine Verbindung zur Runtime
```

Jeder Empty State sagt:

```text
Was fehlt?
Warum ist es leer?
Was kann ich als Nächstes tun?
```

---

## Naming-Konventionen

| Was | Format | Beispiel |
|---|---|---|
| React-Komponenten | `PascalCase.tsx` | `ChatWindow.tsx` |
| Hooks | `camelCase.ts` mit `use` | `useChatStream.ts` |
| Stores | `camelCase.ts` | `windowStore.ts` |
| Contracts | `camelCase.ts` | `chatEvents.ts` |
| Utils | `camelCase.ts` | `formatBytes.ts` |
| CSS-Klassen | Tailwind bevorzugt | `flex items-center` |
| Feature-Ordner | `kebab-case` oder `snake_case`, aber einheitlich | `chat` |
| App IDs | `kebab-case` | `mcp-tools` |
| Event Types | `snake_case` | `tool_result` |

---

## Was die WebUI nicht werden darf

| Problem | Regel |
|---|---|
| riesige `index.html` | Komponenten splitten |
| riesige `style.css` | Tailwind + kleine Komponenten |
| globale JS-Datei mit allem | Feature-Struktur |
| UI erfindet Runtime-State | Backend/Event-Stream ist Wahrheit |
| App-Launcher kennt alle Sonderfälle | App Registry |
| Drag & Drop verändert Fachlogik | Drag verändert nur Layout |
| Fehler nur in Konsole | Fehler sichtbar machen |
| Plugins greifen überall rein | Manifest + Permissions |
| Terminal ohne Kontext | Container/Session sichtbar anzeigen |
| Logs fluten UI | Filter + Virtualisierung |
| hübsche Fake-Erfolge | nur bestätigte Events als Erfolg |

---

## Klare Entscheidung

Die TRION WebUI v2 sollte nicht weiter als Vanilla-JS-Monolith wachsen.

Empfohlene Richtung:

```text
Vite + React + TypeScript + Tailwind + shadcn/ui
```

Dazu:

```text
dnd-kit für Drag & Drop
Framer Motion für Animationen
Zustand für UI-State
xterm.js für Terminal
Monaco Editor für Code/Config
```

---

## Kurzfazit

Die WebUI ist die sichtbare Oberfläche von TRION.

Wenn die WebUI chaotisch wird, wirkt TRION chaotisch.

Deshalb gilt:

```text
Keine Monster-Dateien.
Keine erfundene Wahrheit.
Keine versteckte Sicherheit.
Keine vermischte Logik.
Keine UI ohne Feedback.
```

Ziel:

```text
TRION soll sich anfühlen wie ein kleines lokales AI-Betriebssystem.
Nicht wie ein Admin-Panel.
Nicht wie eine Demo-Seite.
Nicht wie Jarvis mit schönerem CSS.
```
