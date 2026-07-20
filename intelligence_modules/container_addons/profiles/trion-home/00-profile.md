---
id: trion-home-profile
title: TRION Home Workspace Profile
scope: container_profile
applies_to:
  blueprint_ids: [trion-home]
  image_refs: [python:3.12-slim]
  container_tags: [system, persistent, home]
tags:
  - home
  - persistent
  - workspace
  - python
priority: 100
retrieval_hints:
  - what container is this
  - trion home
  - home workspace
  - persistent workspace
  - where do i live
  - my home
confidence: high
last_reviewed: 2026-05-25
---

# Summary

Zielprofil fuer den offiziellen `trion-home`-Blueprint im `container-commander`.
Diese Datei beschreibt Home-Semantik und Arbeitsraum-Idee, aber keine
verifizierte Runtime-Wahrheit.

Ob ein konkreter Container wirklich als Home gilt, entscheidet nur ein
verifizierter `home_context`.

## Identity

- **Blueprint**: `trion-home`
- **Runtime-Profil**: Home-Workspace fuer TRION
- **Zweck**: Persistenter Arbeitsbereich fuer Notizen, Scratch, Workspace und Artefakte
- **Quelle der Wahrheit**: `container_inspect` + `home_manifest` + `home_context.verified=true`

## Zielstruktur

```
/home/trion/
├── .trion/          — Home-Manifest und maschinenlesbare Metadaten
├── notes/           — langfristige Notizen und Entscheidungen
├── diary/           — Laufnotizen und Reflexion
├── scratch/         — harmlose Experimente und temporäre Arbeit
├── workspace/       — laufende Projekte und Arbeitsdateien
├── artifacts/       — generierte Outputs
└── memory/          — system-managed, nicht manuell bearbeiten
```

## Prinzip

- `memory/` wird vom System verwaltet — dort nicht direkt schreiben.
- Schreibrechte ergeben sich nicht aus diesem Text, sondern aus `allowed_write_roots`
  und verifizierten Capability-Klassen.
- Home-Sprache wie „mein Zuhause“ ist erst bei `home_context.verified=true` zulässig.

## Prefer

- Bei neuen Aufgaben zuerst `workspace/`, `notes/` und `artifacts/` prüfen.
- Wiederverwendbare Logik als Arbeitsartefakt im Workspace halten, nicht als
  implizite Runtime-Annahme behandeln.
- Home immer als verifizierten Arbeitsraum beschreiben, nicht als freie Persona-Behauptung.

## Avoid

- Direkt in `memory/` schreiben — das übernimmt das System.
- Aus diesem Profiltext Schreibrechte oder Toolverfügbarkeit ableiten.
- `trion-home` ohne `home_context.verified=true` als sicher bestätigtes Zuhause behandeln.
