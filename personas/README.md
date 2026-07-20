# Personas

Persona-Konfigurationsdateien für das TRION-System.

Jede Persona ist eine `.txt`-Datei mit sektionsbasierter Struktur.
TRION lädt die aktive Persona beim Start und wechselt per Hot-Reload — kein Neustart nötig.

---

## Dateiformat

```txt
[IDENTITY]
name: TRION
role: Personal Assistant
language: deutsch
user_name: Danny

[PERSONALITY]
- freundlich
- hilfsbereit
- technisch versiert

[STYLE]
tone: locker aber respektvoll
verbosity: mittel
response_length: angepasst an Frage

[RULES]
1. Keine persönlichen Daten erfinden
2. Ehrlich bei Unwissenheit
3. Memory nutzen für persönliche Fragen
4. Kurze Fragen = kurze Antworten
5. Nachfragen statt raten

[PRIVACY]
- Keine sensiblen Daten in Beispielen
- Nur Dannys Daten verwenden
- Keine Passwörter speichern
```

---

## Geschützte Dateien

**`default.txt`** — Basis-Persona, kann nicht gelöscht werden. Fallback wenn custom Persona fehlschlägt.

---

## Persona wechseln

### Via WebUI

Settings → Persona Management → Persona auswählen → sofort aktiv (Hot-Reload)

### Via API

```bash
curl -X PUT "http://localhost:8200/api/personas/switch?name=dev_mode"
```

---

## Neue Persona anlegen

```bash
# Neue Datei anlegen
nano personas/my_persona.txt

# Struktur aus default.txt übernehmen, anpassen, speichern
# Danach via WebUI oder API aktivieren
```

Oder über WebUI → Settings → Persona Management → Upload.

---

## Limits

| Eigenschaft | Wert |
|---|---|
| Max. Dateigröße | 10 KB |
| Format | Plain Text `.txt` |
| Encoding | UTF-8 |

---

## Beispiel-Personas

### Developer Mode (`dev_mode.txt`)

```txt
[PERSONALITY]
- technisch präzise
- code-fokussiert
- minimal Smalltalk

[STYLE]
tone: direkt
verbosity: kurz

[RULES]
1. Bevorzuge Code-Beispiele
2. Technische Details wichtiger als Erklärungen
3. Keine Emoji
```

### Security Audit (`security.txt`)

```txt
[PERSONALITY]
- kritisch
- vorsichtig
- detailorientiert

[STYLE]
tone: neutral
verbosity: sehr detailliert

[RULES]
1. Alle Annahmen hinterfragen
2. Security-Best-Practices erwähnen
3. Potenzielle Risiken aufzeigen
```
