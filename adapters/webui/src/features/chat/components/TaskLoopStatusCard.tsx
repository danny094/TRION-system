import { LoaderCircle, PauseCircle, RefreshCw, ShieldAlert, Square, CheckCircle2, Play } from 'lucide-react'
import type { ChatEvent, TaskLoopStateEvent, TaskLoopWaitingEvent } from '@/lib/contracts/chatEvents'
import { cn } from '@/lib/utils'

interface TaskLoopStatusCardProps {
  events: ChatEvent[]
  isBusy: boolean
  onApprove: (taskId: string) => void
}

const STATE_LABELS: Record<string, string> = {
  executing: 'Executing',
  reflecting: 'Reflecting',
  replanning: 'Replanning',
  waiting: 'Waiting for approval',
  completed: 'Completed',
  cancelled: 'Cancelled',
  blocked: 'Blocked',
}

const STOP_REASON_LABELS: Record<string, string> = {
  risk_gate_required: 'Risk gate requires approval',
  user_decision_needed: 'Waiting for a user decision',
  step_failed: 'A task-loop step failed',
  replan_budget_exhausted: 'Replanning budget exhausted',
  failure_abort_policy: 'Error behavior stopped the task loop after a failed step',
  max_steps_reached: 'Maximum step budget reached',
  no_progress: 'No progress detected',
  user_cancelled: 'User cancelled the task loop',
}

function getLatestState(events: ChatEvent[]): TaskLoopStateEvent | null {
  const stateEvents = events.filter((event): event is TaskLoopStateEvent => event.type === 'task_loop_state')
  return stateEvents.at(-1) ?? null
}

function getWaitingTask(events: ChatEvent[]): TaskLoopWaitingEvent | null {
  const waitingEvents = events.filter((event): event is TaskLoopWaitingEvent => event.type === 'task_loop_waiting')
  return waitingEvents.at(-1) ?? null
}

function StateIcon({ state }: { state: string }) {
  if (state === 'executing' || state === 'reflecting') return <LoaderCircle className="w-4 h-4 animate-spin" />
  if (state === 'replanning') return <RefreshCw className="w-4 h-4" />
  if (state === 'waiting') return <PauseCircle className="w-4 h-4" />
  if (state === 'blocked') return <ShieldAlert className="w-4 h-4" />
  if (state === 'cancelled') return <Square className="w-4 h-4" />
  return <CheckCircle2 className="w-4 h-4" />
}

export function TaskLoopStatusCard({ events, isBusy, onApprove }: TaskLoopStatusCardProps) {
  const latestState = getLatestState(events)
  const waitingTask = getWaitingTask(events)

  if (!latestState && !waitingTask) return null

  const state = latestState?.state ?? waitingTask?.state ?? 'waiting'
  const stopReason = latestState?.stop_reason ?? waitingTask?.stop_reason ?? null
  const stepIndex = typeof latestState?.step_index === 'number' ? latestState.step_index + 1 : null
  const totalSteps = typeof latestState?.total_steps === 'number' && latestState.total_steps > 0
    ? latestState.total_steps
    : null
  const completedCount = latestState?.completed_count ?? waitingTask?.completed_count ?? 0
  const statusTone = state === 'waiting'
    ? 'border-amber-400/20 bg-amber-500/10 text-amber-100'
    : state === 'replanning'
      ? 'border-sky-400/20 bg-sky-500/10 text-sky-100'
      : state === 'cancelled' || state === 'blocked'
        ? 'border-rose-400/20 bg-rose-500/10 text-rose-100'
        : state === 'completed'
          ? 'border-emerald-400/20 bg-emerald-500/10 text-emerald-100'
          : 'border-white/10 bg-white/5 text-white/80'

  return (
    <div className={cn('rounded-2xl border px-4 py-3 text-xs', statusTone)}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <StateIcon state={state} />
          <div>
            <div className="font-semibold uppercase tracking-[0.18em] text-[10px] opacity-70">
              Task Loop
            </div>
            <div className="text-sm font-medium">
              {STATE_LABELS[state] ?? state}
            </div>
          </div>
        </div>

        {waitingTask?.task_id && state === 'waiting' && (
          <button
            type="button"
            onClick={() => onApprove(waitingTask.task_id)}
            disabled={isBusy}
            className="inline-flex items-center gap-1 rounded-xl border border-emerald-400/30 bg-emerald-500/15 px-3 py-1.5 text-[11px] font-medium text-emerald-100 transition hover:bg-emerald-500/25 disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5" />
            Continue
          </button>
        )}
      </div>

      <div className="mt-3 grid gap-2 text-[11px] text-current/80">
        {stepIndex && totalSteps ? (
          <div>Step {stepIndex} / {totalSteps}</div>
        ) : totalSteps ? (
          <div>{completedCount} of {totalSteps} steps completed</div>
        ) : null}
        {stopReason ? <div>Reason: {STOP_REASON_LABELS[stopReason] ?? stopReason}</div> : null}
        {waitingTask?.task_id ? <div className="font-mono opacity-70">Task: {waitingTask.task_id}</div> : null}
      </div>
    </div>
  )
}
