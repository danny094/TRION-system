---
id: trion-home-tools
title: TRION Home Tools & Safety
scope: safety
applies_to:
  blueprint_ids: [trion-home]
  image_refs: [python:3.12-slim]
  container_tags: [system, persistent, home]
tags:
  - tools
  - safety
  - python
  - commands
priority: 85
retrieval_hints:
  - what tools do i have
  - available commands
  - python tools
  - safety rules
  - what should i avoid
  - destructive commands
  - data loss
commands_available:
  - python3
  - pip
  - bash
  - find
  - grep
  - curl
  - base64
confidence: high
last_reviewed: 2026-05-25
---

# Summary

Profilwissen zu Werkzeugen und Vorsichtregeln fuer den offiziellen
`trion-home`-Blueprint. Diese Datei ist keine Live-Toolliste und kein Beweis
fuer aktuelle Schreib- oder Exec-Rechte.

## Python als Hauptwerkzeug

Wenn die Runtime es bestaetigt, ist Python das bevorzugte Werkzeug fuer:
- Dateiverarbeitung
- Textanalyse und -generierung
- Berechnungen
- Datenstrukturen und Serialisierung (json, csv, yaml via stdlib)
- lokale Dateiverarbeitung und harmlose Automatisierung

Dieses Profil beweist nie, dass `python3`, `bash` oder Shell-Kommandos live
verfuegbar sind. Das muss immer aus Tool-Ergebnissen kommen.

## Safety — Vorsichtsregeln für Home

Das Home-Volume ist persistent. Fehler wirken nach dem Neustart weiter.

Wichtige Regeln:
- `exec` ersetzt kein sicheres `file_write` oder `file_append`
- Schreibvorgaenge nur in verifizierten `allowed_write_roots`
- `memory/` nie manuell veraendern
- riskante oder destruktive Aktionen bleiben approval-pflichtig

## Prefer

- Toolverfuegbarkeit immer live pruefen
- fehlende Write-Capability offen benennen statt `exec` zu missbrauchen
- Dateioperationen nach dem Schreiben erneut verifizieren

## Avoid

- aus diesem Profiltext direkte Toolrechte ableiten
- `exec` als Hintertuer fuer fehlende Schreibtools benutzen
- sensible Daten in normale Home-Dateien schreiben
