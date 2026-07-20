---
id: trion-home-runtime
title: TRION Home Runtime
scope: runtime
applies_to:
  blueprint_ids: [trion-home]
  image_refs: [python:3.12-slim]
  container_tags: [system, persistent, home]
tags:
  - python
  - debian
  - slim
  - runtime
priority: 95
retrieval_hints:
  - python version
  - package manager
  - what is installed
  - install package
  - pip
  - apt
  - runtime environment
  - init system
commands_available:
  - python3
  - pip
  - pip3
  - apt-get
  - bash
  - sh
  - ls
  - cat
  - echo
  - mkdir
  - cp
  - mv
  - rm
  - find
  - grep
  - curl
  - wget
  - base64
  - date
  - env
confidence: high
last_reviewed: 2026-05-25
---

# Summary

Ziel-Runtime fuer den offiziellen `trion-home`-Blueprint.
Dieser Text ist Profilwissen fuer Thinking und Diagnostics, aber kein Ersatz fuer
`container_inspect`, `home_manifest` oder verifizierte Capability-Discovery.

## Environment

- **Ziel-Image**: `python:3.12-slim`
- **Home-Root**: `/home/trion`
- **Runtime-Profil**: Home-Workspace, kein Dienstcontainer
- **Quelle der Wahrheit**: Live-Runtime immer ueber `container_inspect` und `home_context`

## Wichtig

- Kommandos, Pakete und Netzwerk nie aus diesem Profiltext als live verifiziert behandeln.
- Ob `python3`, `pip`, `bash` oder Netzpfade real verfuegbar sind, muss aus der
  Runtime oder aus echten Tool-Ergebnissen kommen.

## Erwartete Runtime

- Python 3.12
- Shell-Basiswerkzeuge
- persistentes Home unter `/home/trion`
- keine Aussage ueber Live-Verfuegbarkeit ohne Verifikation

## Was dieses Profil nicht beweist

- keine garantierten Schreibrechte
- keine garantierte Toolliste
- keine garantierte Paketliste
- keine garantierten Netzwerkrechte

## Prefer

- Runtime-Fragen zuerst ueber verifizierte Container-/File-Capabilities beantworten.
- Schreiben nur bei bestaetigter Write-Capability und erlaubtem Root planen.
- Profiltext als Diagnose-Hilfe nutzen, nicht als Runtime-Beweis.

## Avoid

- Schreib- oder Exec-Rechte aus dem Profiltext ableiten.
- `exec` als Ersatz fuer fehlende `file_write`-/`file_append`-Capabilities benutzen.
- den aktuellen Compose-Testcontainer mit dieser Ziel-Runtime verwechseln.
