# Container Commander v2 — MCP Server

Produktvertrag: read-only Phase 1 mit exakt fuenf freigegebenen Tools.

Fuehrende Architekturquelle:
- `docs/mcp/24-container-commander.md`

Freigegebene Phase-1-Tools:
- `container_list`
- `container_inspect`
- `container_logs`
- `blueprint_list`
- `blueprint_get`

Aktueller Implementierungs-Iststand:
- Entry-Point und Referenzbundle registrieren noch alle 46 source-deklarierten
  Tools: 20 `read_only` und 26 `mutating`
- die 41 weiteren Tools sind nach P17-SP0 Wahl B keine freigegebene
  Produktoberflaeche; die breite Registrierung ist P17-SP3-Drift
- `risk=read_only` und technische Registrierung ersetzen kein Phase-/Runtime-
  Gate
- mutierende Tools bleiben zusaetzlich bis zum P16-Sicherheitsgate BLOCKED

Wichtige Regeln:
- keine UI-Logik im MCP
- kein Terminal im Commander
- keine Deploy-/Approval-/Hardware-Logik in Phase 1
- Doc24 ist die einzige fachliche Produktwahrheit; diese README spiegelt nur
  den dort entschiedenen Vertrag und den aktuellen Drift-Iststand
- unter `adapters/admin-api/vendor/container_commander/` liegt nur noch ein
  historischer README-Rest; er enthaelt keine Produktlogik und ist kein
  Runtime-, Migrations- oder MCP-Server-Owner
