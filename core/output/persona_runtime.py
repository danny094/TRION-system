from typing import Any, Dict

# Capability-Erkennungsregeln: intelligence_modules/cim_skill_rag/persona_capability_rules.csv
# (PIANO 1.0 Schritt 3.2, 2026-06-11)
from intelligence_modules.cim_skill_rag.persona_capability_loader import load_persona_capability_rules

from core.persona import get_persona


def get_runtime_persona_prompt(context: Dict[str, Any]) -> str:
    persona = get_persona()
    dynamic_context = _dynamic_context(context)
    return persona.build_system_prompt(dynamic_context=dynamic_context).strip()


def _dynamic_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Doc 36 Regel 5 (Prompt-Provenance):
    Injiziert: boolesche Capability-Flags (z.B. "kann Container inspizieren").
    Quelle: context["orchestrator"]["available_tool_details"] - die bereits
    durch Live-Discovery INTERSECT Registry Mirror gefilterte ToolDescriptor-
    Projektion aus core/pipeline/orchestrator_stage.py, NICHT das rohe
    `tool_intent`-Bundle-/Mirror-Format und NICHT `available_tools` (nur
    Namens-Strings, siehe orchestrator_stage.py Z.48 - vor P11.0 SP4 las diese
    Funktion faelschlich aus dieser Namensliste und war dadurch in Produktion
    wirkungslos, da `isinstance(tool, dict)` fuer Strings immer False ist).
    Gefiltert gegen: intelligence_modules/cim_skill_rag/persona_capability_rules.csv
    (domain_eq auf `capability_domain`, name_prefix/name_contains auf `name`,
    description_contains auf `description`).
    """
    orchestrator = context.get("orchestrator")
    if not isinstance(orchestrator, dict):
        return {}

    tools = orchestrator.get("available_tool_details")
    if not isinstance(tools, list) or not tools:
        return {}

    rules = load_persona_capability_rules()
    capabilities: Dict[str, bool] = {flag: False for flag in rules}

    for tool in tools[:24]:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or "").strip().lower()
        domain = str(tool.get("capability_domain") or "").strip().lower()
        description = str(tool.get("description") or "").strip().lower()

        for flag, matchers in rules.items():
            if capabilities[flag]:
                continue
            for match_type, value in matchers:
                if match_type == "domain_eq" and domain == value:
                    capabilities[flag] = True
                    break
                elif match_type == "name_prefix" and name.startswith(value):
                    capabilities[flag] = True
                    break
                elif match_type == "name_contains" and value in name:
                    capabilities[flag] = True
                    break
                elif match_type == "description_contains" and value in description:
                    capabilities[flag] = True
                    break

    return {"capabilities": capabilities} if any(capabilities.values()) else {}
