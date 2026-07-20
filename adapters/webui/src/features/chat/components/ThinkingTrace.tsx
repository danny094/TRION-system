import { motion } from 'framer-motion'
import type {
  ChatEvent,
  ClassifierResultEvent,
  ThinkingPlanEvent,
  VerifierResultEvent,
  TaskLoopStateEvent,
} from '@/lib/contracts/chatEvents'
import { cn } from '@/lib/utils'

type Tone = 'default' | 'success' | 'warning' | 'error'

interface TraceLine {
  key: string
  stage: string
  detail: string
  tone: Tone
  sub?: string
}

interface ToolEventLike {
  success?: unknown
  status?: unknown
}

function eventToLine(event: ChatEvent, index: number): TraceLine | null {
  const key = `${event.type}-${index}`
  switch (event.type) {
    case 'classifier_result': {
      const c = event as ClassifierResultEvent
      const parts = [c.category, c.route, c.safety_level].filter(Boolean) as string[]
      return { key, stage: 'classifying', detail: parts.join(' / ') || '—', tone: 'default' }
    }
    case 'thinking_plan': {
      const p = event as ThinkingPlanEvent
      const stepCount = typeof p.step_count === 'number' ? p.step_count : 0
      const stepStr = stepCount > 0 ? ` · ${stepCount} step${stepCount === 1 ? '' : 's'}` : ''
      return { key, stage: 'planning', detail: `plan${stepStr}`, tone: 'default' }
    }
    case 'verifier_result': {
      const v = event as VerifierResultEvent
      const verdict = String(v.verdict ?? '').trim() || 'pending'
      const tone: Tone = verdict.toLowerCase() === 'approved' ? 'success' : 'warning'
      return { key, stage: 'verifying', detail: verdict, tone }
    }
    case 'task_loop_state': {
      const s = event as TaskLoopStateEvent
      const state = String(s.state ?? '')
      if (state === 'completed') return null
      if (state === 'waiting') {
        return { key, stage: 'task loop', detail: 'waiting', tone: 'warning' }
      }
      if (state === 'replanning') return { key, stage: 'task loop', detail: 'replanning', tone: 'default' }
      if (state === 'blocked') return { key, stage: 'task loop', detail: 'blocked', tone: 'error' }
      if (state === 'cancelled') return { key, stage: 'task loop', detail: 'cancelled', tone: 'warning' }
      const stepPart = typeof s.step_index === 'number' && typeof s.total_steps === 'number' && s.total_steps > 0
        ? ` step ${(s.step_index ?? 0) + 1}/${s.total_steps}`
        : ''
      return { key, stage: 'task loop', detail: `${state}${stepPart}`, tone: 'default' }
    }
    case 'tool_start': {
      return { key, stage: 'tool', detail: 'running', tone: 'default' }
    }
    case 'tool_result': {
      const data = event as unknown as ToolEventLike
      if (data.success === true) {
        return { key, stage: 'tool', detail: 'completed', tone: 'success' }
      }
      return { key, stage: 'tool', detail: 'failed', tone: 'error' }
    }
    default:
      return null
  }
}

function buildLines(events: ChatEvent[]): TraceLine[] {
  const lines: TraceLine[] = []
  let lastStateKey: string | null = null

  events.forEach((event, index) => {
    if (event.type === 'task_loop_state') {
      const s = event as TaskLoopStateEvent
      const key = `${s.state}|${s.step_index ?? ''}|${s.total_steps ?? ''}`
      if (key === lastStateKey) return
      lastStateKey = key
    }
    const line = eventToLine(event, index)
    if (line) lines.push(line)
  })

  return lines
}

const TONE_CLASS: Record<Tone, string> = {
  default: 'text-white/72',
  success: 'text-emerald-300/85',
  warning: 'text-amber-200/85',
  error: 'text-rose-300/85',
}

function Line({ stage, detail, tone, sub }: TraceLine) {
  return (
    <div className="leading-snug">
      <div className={cn('flex gap-3', TONE_CLASS[tone])}>
        <span className="inline-block min-w-[80px] shrink-0 pt-0.5 text-[10px] uppercase tracking-[0.14em] text-white/40">
          {stage}
        </span>
        <span className="flex-1 break-words">{detail}</span>
      </div>
      {sub ? (
        <div className="mt-0.5 pl-[92px] text-[11px] leading-snug text-white/42 break-words">
          {sub}
        </div>
      ) : null}
    </div>
  )
}

export function ThinkingTrace({ events, isStreaming }: { events: ChatEvent[]; isStreaming: boolean }) {
  const lines = buildLines(events)
  if (lines.length === 0 && !isStreaming) return null

  return (
    <details className="group rounded-xl border border-white/5 bg-black/25 shadow-[inset_0_1px_2px_rgba(0,0,0,0.45),inset_0_-1px_0_rgba(255,255,255,0.025)]">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-1.5 text-white/55 hover:text-white/75">
        <span className="inline-block text-[12px] leading-none text-white/35 transition-transform duration-150 group-open:rotate-90">
          &rsaquo;
        </span>
        <span className="text-[10px] uppercase tracking-[0.2em]">
          Thinking
        </span>
        {isStreaming ? (
          <motion.span
            animate={{ opacity: [0.25, 0.9, 0.25] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
            className="ml-1 inline-block h-1 w-1 rounded-full bg-white/55"
          />
        ) : null}
      </summary>
      <div className="border-t border-white/5 px-3 py-2 space-y-1 text-[11px]">
        {lines.length === 0 ? (
          <div className="italic text-white/35">waiting for pipeline…</div>
        ) : (
          lines.map((line) => (
            <Line
              key={line.key}
              stage={line.stage}
              detail={line.detail}
              tone={line.tone}
              sub={line.sub}
            />
          ))
        )}
        {isStreaming && lines.length > 0 ? (
          <motion.div
            animate={{ opacity: [0.15, 0.6, 0.15] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
            className="ml-[92px] h-2 w-[5px] rounded-sm bg-white/40"
          />
        ) : null}
      </div>
    </details>
  )
}
