# Container Commander — Historical Vendor Marker

Dieser Pfad ist **kein eigenständiger MCP-Server**, **keine führende
Produktlogik** und **keine Kompatibilitätslaufzeit**.

Aktueller Bestand:
- ausschließlich dieses historische README
- keine Python-Dateien, Re-Exports, Namespace-Bindings oder Registrierungen
- keine Runtime-, Build- oder Importkopplung

Wichtige Invarianten:
- der produktive Code unter `adapters/admin-api/` importiert nicht direkt aus
  `container_commander` oder `vendor.container_commander`
- der Baum enthält keine eigene Produktlogik mehr
- der Baum ist nicht Teil des Runtime-Images

Der führende Migrations- und Zustandsnachweis liegt in:
- `docs/implementation-plans/completed/46-container-commander-mcp-migration-plan-2026-06-02.md`
- den Guardrails unter `tests/test_vendor_commander_*`

Kurz gesagt:
- **historical-only**
- **logicless**
- **runtime-unwired**
