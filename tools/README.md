# Tools — Tool Executor

Führt Tool-Calls aus die vom Task Loop angefordert werden.
Sitzt zwischen `core/task_loop/executor.py` und den MCP-Servern.

---

## Status

- ✅ `contracts.py` implementiert
- ✅ `executor.py` implementiert und über `tests/test_tools_executor.py` abgedeckt

---

## Modulstruktur

```
tools/
├── __init__.py      ← Einstiegspunkt
├── executor.py      ← Haupt-Executor: nimmt Tool-Call entgegen, routet zu MCP
├── contracts.py     ← ToolCall, ToolResult Datenstrukturen
└── README.md
```

---

## Dateien

### `executor.py`
Nimmt einen `ToolCall` vom Task Loop entgegen und gibt ein `ToolResult` zurück.
Ruft `mcp/client.py → call_tool()` auf.
Behandelt Timeout, Fehler und gibt immer ein strukturiertes Ergebnis zurück.
**Max 100 Zeilen.**

### `contracts.py`
Datenstrukturen: `ToolCall`, `ToolResult`.
Importiert nichts aus dem eigenen Modul.
**Max 60 Zeilen.**

```python
@dataclass
class ToolCall:
    tool_name: str
    arguments: Dict[str, Any]
    step_id: str
    timeout_s: float = 30.0

@dataclass
class ToolResult:
    tool_name: str
    step_id: str
    success: bool
    result: Dict[str, Any]
    error: Optional[str]
    duration_s: float
```

---

## Regeln

- **Kein direkter Docker/System-Aufruf** — alles geht über MCP
- **Immer ein ToolResult zurückgeben** — nie eine Exception werfen
- **Timeout wird immer eingehalten** — kein unbegrenztes Warten
- **Max 100 Zeilen pro Datei**

---

## Wie es in die Pipeline passt

```
core/task_loop/executor.py
        ↓
tools/executor.py → ToolResult
        ↓
mcp/client.py → call_tool()
        ↓
mcp/hub.py → MCP-Server
```
