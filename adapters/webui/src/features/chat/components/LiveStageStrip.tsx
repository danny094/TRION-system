import { motion, AnimatePresence } from 'framer-motion'
import { Brain, GitBranch, ShieldCheck, Wrench, PauseCircle, RefreshCw, type LucideIcon } from 'lucide-react'
import type {
  ChatEvent,
  ClassifierResultEvent,
  ThinkingPlanEvent,
  VerifierResultEvent,
  TaskLoopStateEvent,
} from '@/lib/contracts/chatEvents'
import { cn } from '@/lib/utils'

type StageTone = 'default' | 'warning' | 'success' | 'error'

interface LiveStage {
  key: string
  label: string
  detail: string
  Icon: LucideIcon
  tone: StageTone
}

interface ToolEventLike {
  type: string
  status?: unknown
  success?: unknown
}

function deriveStage(events: ChatEvent[]): LiveStage | null {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index]
    const type = event.type

    if (type === 'tool_start') {
      return { key: `tool_start-${index}`, label: 'Tool', detail: 'running', Icon: Wrench, tone: 'default' }
    }

    if (type === 'tool_result') {
      const data = event as unknown as ToolEventLike
      const ok = data.success === true
      if (ok) {
        return { key: `tool_result-${index}`, label: 'Tool', detail: 'completed', Icon: Wrench, tone: 'success' }
      }
      return { key: `tool_result-${index}`, label: 'Tool', detail: 'failed', Icon: Wrench, tone: 'error' }
    }

    if (type === 'task_loop_state') {
      const state = event as TaskLoopStateEvent
      const value = String(state.state ?? '')
      if (value === 'replanning') {
        return { key: `tls-${index}`, label: 'Task loop', detail: 'replanning', Icon: RefreshCw, tone: 'default' }
      }
      if (value === 'waiting') {
        return { key: `tls-${index}`, label: 'Task loop', detail: 'waiting', Icon: PauseCircle, tone: 'warning' }
      }
      if (value === 'executing' || value === 'reflecting') {
        const hasStep = typeof state.step_index === 'number' && typeof state.total_steps === 'number' && state.total_steps > 0
        const stepStr = hasStep ? ` step ${(state.step_index ?? 0) + 1}/${state.total_steps}` : ''
        return { key: `tls-${index}`, label: 'Task loop', detail: `${value}${stepStr}`, Icon: GitBranch, tone: 'default' }
      }
      continue
    }

    if (type === 'verifier_result') {
      const verifier = event as VerifierResultEvent
      const verdict = String(verifier.verdict ?? '').trim()
      const tone: StageTone = verdict.toLowerCase() === 'approved' ? 'success' : 'warning'
      return { key: `verifier-${index}`, label: 'Verifying', detail: verdict || 'pending', Icon: ShieldCheck, tone }
    }

    if (type === 'thinking_plan') {
      const plan = event as ThinkingPlanEvent
      const stepCount = typeof plan.step_count === 'number' ? plan.step_count : 0
      const stepStr = stepCount > 0 ? ` (${stepCount} step${stepCount === 1 ? '' : 's'})` : ''
      return { key: `plan-${index}`, label: 'Planning', detail: `plan${stepStr}`, Icon: Brain, tone: 'default' }
    }

    if (type === 'classifier_result') {
      const classifier = event as ClassifierResultEvent
      const detail = [classifier.category, classifier.route].filter(Boolean).join(' / ')
      return { key: `classify-${index}`, label: 'Classifying', detail: detail || 'pending', Icon: GitBranch, tone: 'default' }
    }
  }
  return null
}

const TONE_CLASS: Record<StageTone, string> = {
  default: 'text-white/72',
  warning: 'text-amber-200/85',
  success: 'text-emerald-200/85',
  error: 'text-rose-200/85',
}

export function LiveStageStrip({ events }: { events: ChatEvent[] }) {
  const stage = deriveStage(events)

  if (!stage) {
    return (
      <div className="flex items-center gap-2 text-[12px] text-white/55">
        <motion.span
          animate={{ opacity: [0.45, 1, 0.45] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
        >
          Thinking...
        </motion.span>
      </div>
    )
  }

  const { Icon } = stage
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={stage.key}
        initial={{ opacity: 0, y: 3 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -3 }}
        transition={{ duration: 0.18, ease: 'easeOut' }}
        className={cn('flex items-center gap-2 text-[12px] min-w-0', TONE_CLASS[stage.tone])}
      >
        <Icon className="w-3.5 h-3.5 opacity-75 shrink-0" />
        <span className="font-semibold uppercase tracking-[0.16em] text-[10px] opacity-65 shrink-0">
          {stage.label}
        </span>
        <span className="opacity-45 shrink-0">&rarr;</span>
        <span className="truncate">{stage.detail}</span>
      </motion.div>
    </AnimatePresence>
  )
}
