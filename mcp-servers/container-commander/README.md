# Container Commander v2 — MCP Server

Read-only Phase-1 server for the new Container Commander contract.

Fuehrende Architekturquelle:
- `docs/mcp/24-container-commander.md`

Phase 1 Tools:
- `container_list`
- `container_inspect`
- `container_logs`
- `blueprint_list`
- `blueprint_get`

Wichtige Regeln:
- keine UI-Logik im MCP
- kein Terminal im Commander
- keine Deploy-/Approval-/Hardware-Logik in Phase 1
- die alte Admin-API-Laufzeitbasis liegt getrennt unter
  `adapters/admin-api/vendor/container_commander/`; sie bleibt
  Migrationsquelle, ist aber kein MCP-Server-Pfad mehr
