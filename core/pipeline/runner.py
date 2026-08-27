from typing import Any, Dict, Optional

from core.classifier.classifier import classify
from config import (
    get_task_loop_max_replans,
    get_task_loop_max_retries_per_step,
    get_task_loop_max_steps,
)
from core.models import CoreChatRequest, CoreChatResponse
from core.orchestrator.orchestrator import orchestrate
from core.orchestrator.tools import list_available_tools
from core.output.output import generate_output
from core.pipeline.document_tools_stage import build_document_tools_stage
from core.pipeline.event_stream import PipelineEventSink, classifier_event, emit_pipeline_event, routing_trace_event, thinking_plan_event, verifier_event
from core.pipeline.grounding_stage import (
    inject_recent_grounding_state,
    resolve_grounding_state,
)
from core.pipeline.log import (
    log_classifier,
    log_orchestrator,
    log_output,
    log_request_start,
    log_task_loop,
    log_thinking,
    log_verifier,
)
from core.pipeline.orchestrator_stage import build_orchestrator_stage, replan_tools_with_provenance
from core.pipeline.output_stage import approved_response, build_output_stage, rejected_response
from core.pipeline.plan_contract_validator import tool_truth_from_context, validate_plan_contract
from core.pipeline.preprocess import preprocess_request
from core.pipeline.routing_frame_stage import build_routing_frame_stage
from core.pipeline.runner_contracts import ChunkSink, OrchestratorFn, OutputFn, SemanticSaveFn, TaskEventSink, TaskLoopFn, TaskLoopObserver, ToolRunner, WorkspaceSaveFn
from core.pipeline.task_loop_budget import collect_task_loop_budget
from core.pipeline.task_loop_stage import build_task_loop_stage
from core.pipeline.thinking_stage import build_thinking_stage
from core.task_loop.executor import TaskToolCall, TaskToolResult, TaskToolResultStatus
from core.task_loop.task_loop import start_task_loop
from core.thinking.thinking import build_plan
from core.thinking.replanner import build_replan
from core.verifier.contracts import Verdict, VerifierResult
from core.verifier.verifier import verify_plan

def _default_tool_runner(tool_call: TaskToolCall) -> TaskToolResult:
    return TaskToolResult(
        status=TaskToolResultStatus.TRANSPORT_FAILURE,
        error=f"tool_runner_missing:{tool_call.tool_name or tool_call.step_id}",
    )
async def run_chat(
    request: CoreChatRequest,
    output_fn: OutputFn = generate_output,
    *,
    task_loop_fn: TaskLoopFn = start_task_loop,
    tool_runner: ToolRunner = _default_tool_runner,
    project_output_evidence_item: Any = None,
    orchestrator_fn: OrchestratorFn = orchestrate,
    orchestrator_context_sources: Optional[Dict[str, Any]] = None,
    orchestrator_raw_tools: Any = None,
    replanner_fn: Any = build_replan,
    document_workspace_save_fn: WorkspaceSaveFn | None = None,
    document_semantic_save_fn: SemanticSaveFn | None = None,
    task_loop_observer: TaskLoopObserver | None = None,
    task_event_sink: TaskEventSink | None = None,
    pipeline_event_sink: PipelineEventSink | None = None,
    chunk_sink: ChunkSink | None = None,
    autonomous_mode: bool = False,
) -> CoreChatResponse:
    """Run the first minimal core path from adapter request to adapter response."""
    log_request_start(request.conversation_id, request.get_last_user_message(), request.model)
    preprocessed = preprocess_request(
        request.get_last_user_message(),
        conversation_id=request.conversation_id,
        classify_fn=classify,
        workspace_save_fn=document_workspace_save_fn,
        semantic_save_fn=document_semantic_save_fn,
    )
    history_len = len(request.messages)
    recent_grounding_state = resolve_grounding_state(request.conversation_id, history_len)
    user_text = preprocessed.raw_user_text
    classifier_result = preprocessed.classifier_result
    document_context = preprocessed.document_context
    planning_user_text = preprocessed.planning_user_text
    log_classifier(classifier_result)
    emit_pipeline_event(pipeline_event_sink, classifier_event(classifier_result))
    document_tools_stage = build_document_tools_stage(
        orchestrator_raw_tools,
        document_context,
        user_text=user_text,
    )
    routing_frame_stage = build_routing_frame_stage(
        user_text,
        classifier_result,
        orchestrator_thinking_context=None,
    )
    emit_pipeline_event(pipeline_event_sink, routing_trace_event(routing_frame_stage.context.get("routing_frame")))
    orchestrator_stage = build_orchestrator_stage(
        planning_user_text,
        classifier_result,
        conversation_id=request.conversation_id,
        orchestrator_fn=orchestrator_fn,
        raw_tools=orchestrator_raw_tools,
        context_sources=orchestrator_context_sources,
        routing_frame=routing_frame_stage.context.get("routing_frame") if isinstance(routing_frame_stage.context, dict) else None,
    )
    inject_recent_grounding_state(orchestrator_stage.context, recent_grounding_state)
    log_orchestrator(orchestrator_stage.thinking_context)
    thinking_stage = build_thinking_stage(
        planning_user_text,
        classifier_result,
        build_plan_fn=build_plan,
        orchestrator_thinking_context=orchestrator_stage.thinking_context,
        routing_frame_thinking_context=routing_frame_stage.thinking_context,
        document_tools_thinking_context=document_tools_stage.thinking_context,
        document_context=document_context,
    )
    plan = thinking_stage.plan
    plan_contract = validate_plan_contract(plan, tool_truth_from_context(thinking_stage.thinking_context), context=thinking_stage.thinking_context)
    if not plan_contract.allowed:
        return rejected_response(
            model=request.model,
            conversation_id=request.conversation_id,
            classifier_result=classifier_result,
            verifier_result=VerifierResult(verdict=Verdict.REJECTED, reason=plan_contract.reason),
        )
    log_thinking(plan)
    emit_pipeline_event(pipeline_event_sink, thinking_plan_event(plan))
    verifier_result = verify_plan(
        plan,
        user_text,
        document_context=document_context,
        autonomous_mode=autonomous_mode,
    )
    log_verifier(verifier_result)
    emit_pipeline_event(pipeline_event_sink, verifier_event(verifier_result))
    if verifier_result.verdict != Verdict.APPROVED:
        return rejected_response(
            model=request.model,
            conversation_id=request.conversation_id,
            classifier_result=classifier_result,
            verifier_result=verifier_result,
        )

    replan_available_tools, replan_tool_truth_source = replan_tools_with_provenance(
        orchestrator_stage.context, orchestrator_raw_tools
    )
    receipt_tool_descriptors = list_available_tools(orchestrator_raw_tools)
    task_loop_stage = build_task_loop_stage(
        plan,
        conversation_id=request.conversation_id,
        objective=user_text,
        task_loop_fn=task_loop_fn,
        tool_runner=tool_runner,
        replanner_fn=replanner_fn,
        max_steps=get_task_loop_max_steps(),
        max_retries_per_step=get_task_loop_max_retries_per_step(),
        max_replans=get_task_loop_max_replans(),
        **collect_task_loop_budget(),
        event_sink=task_event_sink,
        available_tools=replan_available_tools,
        receipt_tool_descriptors=receipt_tool_descriptors,
        orchestrator_context=orchestrator_stage.context,
        project_output_evidence_item=project_output_evidence_item,
    )
    log_task_loop(task_loop_stage.result)
    if callable(task_loop_observer) and task_loop_stage.result is not None:
        task_loop_observer(
            plan=getattr(task_loop_stage.result, "active_plan", None) or plan,
            task_loop_result=task_loop_stage.result,
            orchestrator_context=orchestrator_stage.context,
            available_tools=replan_available_tools,
            tool_truth_source=replan_tool_truth_source,
        )
    output_stage = build_output_stage(
        user_text=user_text,
        thinking_plan=getattr(task_loop_stage.result, "active_plan", None) or plan,
        verifier_result=verifier_result,
        orchestrator_context={**orchestrator_stage.context, **routing_frame_stage.context},
        document_tools_context=document_tools_stage.context,
        output_evidence=task_loop_stage.output_evidence,
        document_context=document_context,
        stream=request.stream,
    )
    output_kwargs: Dict[str, Any] = {"chunk_sink": chunk_sink} if chunk_sink is not None else {}
    output_result = await output_fn(output_stage.output_request, request, **output_kwargs)
    log_output(output_result.content)

    return approved_response(
        model=request.model,
        content=output_result.content,
        conversation_id=request.conversation_id,
        classifier_result=classifier_result,
    )
