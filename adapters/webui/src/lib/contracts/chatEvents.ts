/**
 * Chat Event Contract (basiert auf 10-chat-event-contract.md)
 */

export type ChatEventType = 
  | 'content'
  | 'final_content'
  | 'done'
  | 'error'
  | 'rejected'
  | 'blocked'
  | 'status'
  | 'classifier_result'
  | 'routing_trace'
  | 'thinking_plan'
  | 'verifier_result'
  | 'task_loop_state'
  | 'task_loop_waiting'
  | 'tool_start'
  | 'tool_result'
  | 'workspace_update'
  | 'progress_utterance'
  | 'replan_trace'
  | 'task_loop_provenance'

export type DoneReason = 'stop' | 'error' | 'cancelled' | 'blocked' | 'rejected'
export type TaskLoopStateValue = 'executing' | 'reflecting' | 'replanning' | 'completed' | 'waiting' | 'blocked' | 'cancelled'
export type TaskLoopStopReason =
  | 'max_steps_reached'
  | 'step_failed'
  | 'replan_budget_exhausted'
  | 'failure_abort_policy'
  | 'risk_gate_required'
  | 'user_decision_needed'
  | 'no_progress'
  | 'user_cancelled'

export interface BaseChatEvent {
  type: ChatEventType
  model: string
  conversation_id: string
  created_at: string
  done: boolean
}

export interface ContentEvent extends BaseChatEvent {
  type: 'content'
  content: string
}

export interface FinalContentEvent extends BaseChatEvent {
  type: 'final_content'
  content: string
}

export interface DoneEvent extends BaseChatEvent {
  type: 'done'
  done: true
  done_reason: DoneReason
}

export interface TaskLoopStateEvent extends BaseChatEvent {
  type: 'task_loop_state'
  state: TaskLoopStateValue
  step_index?: number
  total_steps?: number
  stop_reason?: TaskLoopStopReason | null
  completed_count?: number
  artifact_count?: number
  replan_count?: number
  max_replans?: number
  max_steps?: number
  no_progress_count?: number
}

export interface TaskLoopWaitingEvent extends BaseChatEvent {
  type: 'task_loop_waiting'
  task_id: string
  state: 'waiting'
  stop_reason?: TaskLoopStopReason | null
  current_step_index?: number
  total_steps?: number
  completed_count?: number
}

export interface ClassifierResultEvent extends BaseChatEvent {
  type: 'classifier_result'
  category?: string
  route?: string
  safety_level?: string
  needs_orchestrator?: boolean
  is_long_document?: boolean
}

export interface ThinkingPlanEvent extends BaseChatEvent {
  type: 'thinking_plan'
  step_count?: number
  needs_task_loop?: boolean
  risk_level?: string
  additional_evidence_present?: boolean
}

export interface VerifierResultEvent extends BaseChatEvent {
  type: 'verifier_result'
  verdict?: 'approved' | 'rejected' | 'hard_block'
}

export interface ProgressUtteranceEvent extends BaseChatEvent {
  type: 'progress_utterance'
  text: string
  trigger_event: 'tool_start' | 'tool_result' | 'task_loop_state'
  stop_reason?: string
}

export interface ReplanTraceEvent extends BaseChatEvent {
  type: 'replan_trace'
  stage?: string
  phase?: 'replan'
  replan_count?: number
  trigger?: string
  failure_status?: string
  step_count?: number
  additional_evidence_present?: boolean
  artifact_count?: number
}

export interface GenericPipelineEvent extends BaseChatEvent {
  type: Exclude<
    ChatEventType,
    'content' | 'final_content' | 'done' | 'task_loop_state' | 'task_loop_waiting' | 'classifier_result' | 'thinking_plan' | 'verifier_result' | 'progress_utterance' | 'replan_trace'
  >
  [key: string]: unknown
}

export type ChatEvent =
  | ContentEvent
  | FinalContentEvent
  | DoneEvent
  | TaskLoopStateEvent
  | TaskLoopWaitingEvent
  | ClassifierResultEvent
  | ThinkingPlanEvent
  | VerifierResultEvent
  | ProgressUtteranceEvent
  | ReplanTraceEvent
  | GenericPipelineEvent
