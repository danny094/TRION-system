---
scope: layer_prompt
target: thinking_active_containers
variables: ["container_context"]
status: active
---

## Aktive Container dieser Session

{container_context}

Beziehe diese Information in deine Tool-Entscheidung ein:

- Wenn der User einen laufenden Container erwähnt — per Name, Blueprint-ID, Tag oder Beschreibung (z.B. "ubuntu container", "python sandbox", "der laufende container") — bevorzuge einen bestehenden aktiven Container-Kontext statt neue Laufzeit anzufordern. Übergib vorhandene `container_id` nur an live verfügbare passende Tools.
- Wenn mehrere Container laufen und der User keinen eindeutigen nennt, wähle den passendsten anhand von Tags und Beschreibung — oder setze `needs_clarification: true`.
- Neue Laufzeit nur anfordern, wenn **kein** passender Container in der Liste läuft.
- Nutze die Tags (z.B. [python, compute], [linux, network]) für semantisches Matching — "python script ausführen" → python-sandbox, "netzwerk test" → ubuntu-network.
