from typing import Any

from core.output.contracts import RenderableEvidence
from core.output.contracts import OutputRequest
from core.output.renderable_evidence import build_renderable_evidence, render_multi_renderable_evidence
from core.output.tool_grounding import collect_grounded_tool_results, render_single_grounded_tool_result


def render_direct_tool_output(output_request: OutputRequest) -> str:
    context = output_request.context if isinstance(output_request.context, dict) else {}
    grounded_results = context.get("grounded_tool_results")
    if not isinstance(grounded_results, list) or not grounded_results:
        grounded_results = collect_grounded_tool_results(context)
    return render_single_grounded_tool_result(grounded_results)


def render_direct_multi_tool_output(output_request: OutputRequest) -> str:
    context = output_request.context if isinstance(output_request.context, dict) else {}
    evidence = context.get("renderable_evidence")
    if not isinstance(evidence, list) or not evidence:
        grounded_results = context.get("grounded_tool_results")
        if not isinstance(grounded_results, list) or not grounded_results:
            grounded_results = collect_grounded_tool_results(context)
        evidence = build_renderable_evidence(grounded_results)
    normalized = [item for item in evidence if isinstance(item, RenderableEvidence)]
    return render_multi_renderable_evidence(normalized)
