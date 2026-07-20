# Container Commander — Vendor Compat Tree

Dieser Baum ist **kein eigenständiger MCP-Server** und **keine führende
Produktlogik** mehr.

Aktueller Zweck:
- repo-kompatible Importpfade für ältere Namespaces
- dünne Re-Exports auf lokale Admin-API-Truth-Sources
- gelegentliche Namespace-Bindings oder MCP-Registrierung ohne eigene Fachlogik

Wichtige Invarianten:
- der produktive Code unter `adapters/admin-api/` importiert nicht direkt aus
  `container_commander` oder `vendor.container_commander`
- der Baum enthält keine eigene Produktlogik mehr
- der Baum ist nicht Teil des Runtime-Images

Der führende Migrations- und Zustandsnachweis liegt in:
- `docs/implementation-plans/completed/46-container-commander-mcp-migration-plan-2026-06-02.md`
- den Guardrails unter `tests/test_vendor_commander_*`

Kurz gesagt:
- **compat-only**
- **logicless**
- **runtime-unwired**
