# Examples

Diese Ordner sind Referenz- und Testbundles fuer den aktuellen TRION-Stand.

## Kanonische Container-Commander-Beispiele

Fuer den aktuellen `container-commander v2`-Livepfad sind genau diese beiden
Ordner die richtige Quelle:

- `container_commander_bundle/`
  - installer-kompatibles MCP-Bundle
  - wird ueber den MCP-Installer als `container-commander` installiert
  - ZIP: `container_commander_bundle.zip`
- `container_commander_plugin/`
  - getrenntes WebUI-Plugin fuer den Commander
  - wird ueber den Plugin-Installer als `container-commander-ui` installiert
  - ZIP: `container_commander_plugin.zip`

Diese beiden Bundles gehoeren zusammen:

1. erst `container_commander_bundle.zip` installieren
2. danach `container_commander_plugin.zip` installieren

## Weitere Referenzen

- `time_mcp_bundle/`
  - einfaches Referenz-MCP fuer den generischen MCP-Installer
- `host_plugin_bundle/`
  - einfaches Referenz-Plugin fuer den generischen Host-/ESM-Pluginpfad

## Wichtige Regel

Nicht alle Example-Ordner sind gleich wichtig.

Wenn es um den aktuellen echten Container-Commander-Stand geht, gelten nur:

- `container_commander_bundle/`
- `container_commander_plugin/`

Die anderen Ordner sind generische Referenzen, nicht der fuehrende
Container-Commander-Pfad.
