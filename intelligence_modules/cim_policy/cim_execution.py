import logging
from typing import Any, Dict

from intelligence_modules.cim_policy.cim_execution_support import (
    _extract_args,
    _extract_search_query,
    _extract_triggers,
    _generate_skill_code,
)
from intelligence_modules.cim_policy.cim_policy_contracts import ActionType, CIMDecision
from mcp.tool_result_contracts import (
    MCPToolCallStatus,
    MCPToolResultEnvelope,
    project_tool_result_wire_mapping,
)


logger = logging.getLogger("intelligence_modules.cim_policy.cim_policy_engine")


def _project_call_result(envelope: MCPToolResultEnvelope) -> tuple[Dict[str, Any], bool]:
    if not isinstance(envelope, MCPToolResultEnvelope):
        raise TypeError("CIM tool calls require MCPToolResultEnvelope")
    return (
        dict(project_tool_result_wire_mapping(envelope)),
        envelope.status is MCPToolCallStatus.SUCCESS,
    )


async def execute_cim_decision(
    decision: CIMDecision,
    user_input: str,
    hub,
) -> Dict[str, Any]:
    """Führt die CIM-Entscheidung aus."""
    if not decision.matched:
        return {"executed": False, "reason": decision.reason}
    action = decision.action
    skill_name = decision.skill_name
    result = {
        "executed": False,
        "action": action.value,
        "skill_name": skill_name,
        "output": None,
        "error": None,
    }
    try:
        if action == ActionType.FORCE_CREATE_SKILL:
            code = await _generate_skill_code(user_input, skill_name, hub)
            create_result = await hub.call_tool_async("create_skill", {
                "name": skill_name,
                "code": code,
                "description": f"Auto-generated skill for: {user_input[:50]}",
                "triggers": _extract_triggers(user_input),
            })
            result["output"], result["executed"] = _project_call_result(create_result)
            if result["executed"]:
                result["created_skill"] = skill_name
            if result["executed"] and decision.policy_match and decision.policy_match.allows_chaining:
                run_result = await hub.call_tool_async("run_skill", {
                    "name": skill_name,
                    "args": _extract_args(user_input),
                })
                result["run_output"], result["executed"] = _project_call_result(run_result)
        elif action == ActionType.FORCE_RUN_SKILL:
            run_result = await hub.call_tool_async("run_skill", {
                "name": skill_name,
                "args": _extract_args(user_input),
            })
            result["output"], result["executed"] = _project_call_result(run_result)
        elif action == ActionType.RUN_SKILL:
            run_result = await hub.call_tool_async("run_skill", {
                "name": skill_name,
                "args": _extract_args(user_input),
            })
            result["output"], result["executed"] = _project_call_result(run_result)
        elif action == ActionType.LIST_SKILLS:
            list_result = await hub.call_tool_async("list_skills", {})
            result["output"], result["executed"] = _project_call_result(list_result)
        elif action == ActionType.WEB_SEARCH:
            query = _extract_search_query(user_input)
            result["output"] = f"[Web-Search für: {query}]"
            result["executed"] = True
            result["needs_external"] = True
        elif action == ActionType.DENY_AUTONOMY:
            result["output"] = "Diese Aktion ist aus Sicherheitsgründen nicht erlaubt."
            result["denied"] = True
        elif action == ActionType.REQUEST_USER_CONFIRMATION:
            result["output"] = (
                f"Soll ich den Skill '{skill_name}' wirklich ausführen/erstellen?"
            )
            result["needs_confirmation"] = True
        elif action == ActionType.FALLBACK_CHAT:
            result["fallback"] = True
    except Exception as error:
        logger.error(f"[CIM] Execution error: {error}")
        result["error"] = str(error)
        result["executed"] = False
        if decision.policy_match and decision.policy_match.fallback_action:
            result["fallback_triggered"] = decision.policy_match.fallback_action.value
    return result
