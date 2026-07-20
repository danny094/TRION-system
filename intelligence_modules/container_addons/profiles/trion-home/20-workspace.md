---
id: trion-home-workspace
title: TRION Home Workspace Structure
scope: diagnostics
applies_to:
  blueprint_ids: [trion-home]
  image_refs: [python:3.12-slim]
  container_tags: [system, persistent, home]
tags:
  - workspace
  - filesystem
  - projects
  - scripts
  - journal
priority: 90
retrieval_hints:
  - where to save files
  - project structure
  - workspace layout
  - where are my scripts
  - journal
  - experiments
  - creative
  - find my work
  - previous work
commands_available:
  - ls
  - find
  - cat
  - mkdir
  - python3
confidence: high
last_reviewed: 2026-05-25
---

# Summary

Zielstruktur des verifizierten `trion-home`-Workspaces unter `/home/trion/`.
Diese Datei beschreibt bevorzugte Ordnung, aber keine Live-Garantie fuer Inhalt,
Schreibrechte oder aktuelle Dateien.

## Verzeichnisse im Detail

### `.trion/`
Maschinenlesbare Home-Metadaten wie `home.json`.

### `notes/`
Langfristige Notizen, Ideen und Entscheidungen.

### `diary/`
Laufnotizen und Reflexion. Nur mit verifizierter Write-Capability.

### `scratch/`
Temporäre, harmlose Experimente und schnelle Tests.

### `workspace/`
Laufende Projekte und Arbeitsdateien.

### `artifacts/`
Generierte Outputs und Ergebnisse.

### `memory/`
System-managed. Nicht manuell bearbeiten.

## Wichtiger Hinweis

Welche Pfade aktuell existieren und schreibbar sind, muss immer aus
`home_manifest`, `allowed_write_roots` und verifizierten Tool-Ergebnissen
kommen.

## Prefer

- Vor neuer Arbeit `workspace/`, `notes/` und `artifacts/` auf vorhandene Kontexte prüfen.
- Neue Dateien in den semantisch passenden Root legen statt flach unter `/home/trion/`.
- `memory/` strikt von normalen Home-Dateien trennen.

## Avoid

- alte Strukturpfade wie `projects/`, `scripts/`, `creative/` als harte Runtime-Wahrheit behandeln
- ohne verifizierte Write-Capability in `diary/`, `notes/` oder `workspace/` planen
- `memory/` manuell bearbeiten
