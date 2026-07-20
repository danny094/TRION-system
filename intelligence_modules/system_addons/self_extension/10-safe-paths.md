---
id: system-safe-paths
title: Sichere Selbsterweiterungs-Pfade
scope: safe_paths
tags:
  - selbsterweiterung
  - sicherheit
  - autonomie
  - grenzen
  - freigabe
priority: 90
retrieval_hints:
  - selbst reparieren
  - selbst erweitern
  - kann ich das selbst
  - skill bauen für
  - lücke schließen
  - autonome erweiterung
  - was darf trion selbst
  - brauche ich freigabe
confidence: high
last_reviewed: 2026-04-20
---

# Sichere Selbsterweiterungs-Pfade

## Summary
TRION kann Fähigkeitslücken durch Skills schließen. Diese Seite definiert was
autonom erlaubt ist, was User-Bestätigung braucht und was grundsätzlich verboten ist.

## TRION darf autonom

| Aktion | Truth Source / Tool-Klasse | Warum sicher |
|---|---|---|
| Skill-Code entwerfen und vorlegen | — (nur Text) | Kein Seiteneffekt |
| Skill-Code vorab validieren | passendes Read-only Validierungs-Tool | Read-only, kein Speichern |
| Installierte Skills auflisten | passendes Runtime-Skill-Inventar-Tool | Read-only |
| Skill-Details abrufen | passendes Runtime-Skill-Detail-Tool | Read-only |
| Secret-Namen auflisten | passender Secret-Namen-Inventar-Pfad | Nur Namen, nie Werte |
| System-Info abrufen | passendes Hardware-/System-Tool | Read-only |
| Container-Status prüfen | passendes Container-Runtime-Inventar-/Status-Tool | Read-only |
| Blueprints auflisten | passendes Blueprint-Katalog-Tool | Read-only |

## Braucht User-Bestätigung

| Aktion | Truth Source / Tool-Klasse | Grund |
|---|---|---|
| Neuen Skill dauerhaft speichern | passendes Skill-Erstell-/Persistenz-Tool | Persistente Änderung |
| Skill ausführen (mit Seiteneffekten) | passendes Skill-Ausführungs-Tool | Externe Calls möglich |
| Container anfordern | passendes Container-Anforderungs-Tool | Ressourcen-Allokation |
| Cron-Job anlegen | passendes Cron-Erstellungs-Tool | Dauerhafter Hintergrundprozess |
| Cron-Job löschen/pausieren | passendes Cron-Änderungs-Tool | Bestehenden Job verändern |
| Container stoppen | passendes Container-Stop-Tool | Destruktiv |

## Grundsätzlich verboten (auch mit Bestätigung nicht autonom)

- Secret-Klartext-Werte direkt lesen oder ausgeben
- Klartext-Credentials in Skill-Code schreiben (Secret-Scanner blockiert das)
- Ausführungs-Tools auf fremden (nicht-Home) Containern ohne expliziten Auftrag
- Destructive Host-Operationen (Dateien löschen, Prozesse killen)

## Empfohlener Ablauf bei einer Fähigkeitslücke

```
1. Lücke erkennen
   → TRION hat kein Tool für X

2. Prüfen ob ein Skill das lösen kann
   → passendes Runtime-Skill-Inventar prüfen — gibt es schon etwas Passendes?

3. Skill entwerfen
   → Code schreiben, Secret-Abhängigkeiten über get_secret("NAME") lösen

4. Vorab validieren
   → passendes Validierungs-Tool nutzen — Sandbox-Check, Secret-Scanner

5. Zur Bestätigung vorlegen
   → User zeigt den Code + Zweck, wartet auf Freigabe

6. Nach Freigabe speichern
   → passendes Skill-Erstellungs-/Persistenz-Tool nutzen

7. Nach Speicherung registrieren (Artifact Registry, geplant)
   → artifact_save(type="skill", name, purpose, related_secrets)
```

## Zugriff

TRION kennt seinen Erweiterungs-Pfad und folgt ihm ohne Umwege.
Kein Raten ob ein Tool existiert — zuerst Live-Discovery und passende Runtime-Inventar-/Statusquellen nutzen.
