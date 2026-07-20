"""
adapters.tool_runner_bridge
============================
Brücke zwischen core/task_loop und tools/executor → MCP Hub.

Warum hier: core/ darf nicht aus tools/ importieren (Import-Hierarchie).
adapters/ ist der einzige Layer der aus beiden importieren darf.

Zwei Aufgaben:
- make_tool_runner(): ToolRunner-Callable für run_chat()
- get_available_tools(): Tool-Liste aus MCP Hub für orchestrator_raw_tools

P11.0 SP4: kein Bundle-Fallback mehr. `_tool_intent_for()` liest ausschliesslich
`config["tool_intents"]` (Registry Mirror) - nie mehr `tool_intents.json` direkt
aus dem Bundle-Verzeichnis. Fehlt der Mirror-Eintrag fuer ein Tool, liefert
diese Funktion `{}`.

P11.0 SP4 Korrektur (Round 2): Eligibility ist eine gemeinsame Predicate-
Funktion - core/orchestrator/tool_descriptor_projection.py::is_eligible_tool_intent().
get_available_tools() ist der primaere Chokepoint: Live-Tools ohne gueltigen
Mirror-Eintrag (fehlende/unvollstaendige/typfalsche `tool_intent_meta`,
unbekannte `schema_version`, ungueltiger Hash/Bundle-Version) oder mit
einem Schema-v2-Eintrag ohne exakt `capability_complete is True` (fehlend,
`False` oder sonstiger Wert) erscheinen gar nicht erst in
orchestrator_raw_tools. Ein Mirror-Eintrag ohne zugehoeriges Live-Tool taucht
ohnehin nicht auf, weil nur ueber `hub.list_tools()` iteriert wird.
`descriptor_from_raw()` wendet dieselbe Predicate-Funktion zusaetzlich als
Fail-closed-Guard an - keine zweite, potenziell abweichende Eligibility-Logik.
Siehe tests/test_tool_intent_truth_source.py und tests/test_tool_runner_bridge.py.
"""
from typing import Any, List

from core.orchestrator.tool_descriptor_projection import is_eligible_tool_intent
from core.task_loop.executor import TaskToolCall, TaskToolResult, ToolRunner
from tools.contracts import ToolCall
from tools.executor import run_tool


def make_tool_runner() -> ToolRunner:
    """Returns a ToolRunner that routes TaskToolCall through tools/executor to MCP Hub."""
    def _run(task_call: TaskToolCall) -> TaskToolResult:
        tool_call = ToolCall(
            tool_name=task_call.tool_name,
            arguments=dict(task_call.arguments or {}),
            step_id=task_call.step_id,
            timeout_s=task_call.timeout_s,
        )
        result = run_tool(tool_call)
        return TaskToolResult(
            success=result.success,
            result=dict(result.result or {}),
            error=result.error,
        )
    return _run


def get_available_tools() -> List[Any]:
    """Returns eligible tools currently registered in MCP Hub. Empty list on failure.

    Eligible heisst: is_eligible_tool_intent() (core/orchestrator/
    tool_descriptor_projection.py) liefert True fuer den Registry-Mirror-
    Eintrag des Tools - siehe dortiger Docstring fuer die genauen Kriterien.
    """
    try:
        from mcp.hub import get_hub
        from mcp.config import get_all_mcps

        hub = get_hub()
        registry = get_all_mcps()
        tools = []
        for tool in hub.list_tools():
            name = str((tool or {}).get("name") or "").strip()
            mcp_name = hub.get_mcp_for_tool(name) or ""
            tool_intent = _tool_intent_for(name, registry.get(mcp_name, {}))
            if not is_eligible_tool_intent(tool_intent):
                continue
            tools.append(
                {
                    **dict(tool or {}),
                    "mcp": mcp_name,
                    "tool_intent": tool_intent,
                }
            )
        return tools
    except Exception:
        return []


def _tool_intent_for(tool_name: str, config: Any) -> dict:
    tool_intents = (config or {}).get("tool_intents") or {}
    tools = tool_intents.get("tools") if isinstance(tool_intents, dict) else []
    if not isinstance(tools, list):
        return {}
    for tool in tools:
        if str((tool or {}).get("name") or "").strip() == tool_name:
            return dict(tool or {})
    return {}
