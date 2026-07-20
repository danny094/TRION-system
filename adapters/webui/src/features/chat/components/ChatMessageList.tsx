import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bot, User } from 'lucide-react'
import { useChatStore } from '../state/chatStore'
import { getActiveSession } from '../lib/sessionSelectors'
import type { Message } from '../types'
import type { ChatEvent, TaskLoopStateEvent } from '@/lib/contracts/chatEvents'
import { cn } from '@/lib/utils'
import { TaskLoopStatusCard } from './TaskLoopStatusCard'
import { ThinkingTrace } from './ThinkingTrace'
import { LiveStageStrip } from './LiveStageStrip'
import { ProgressUtteranceList } from './ProgressUtteranceList'

const ACTIONABLE_LOOP_STATES = new Set(['waiting', 'blocked', 'cancelled'])

function shouldShowStatusCard(events: ChatEvent[]): boolean {
  if (events.some((event) => event.type === 'task_loop_waiting')) return true
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index]
    if (event.type === 'task_loop_state') {
      const state = String((event as TaskLoopStateEvent).state ?? '')
      return ACTIONABLE_LOOP_STATES.has(state)
    }
  }
  return false
}

function StreamingCursor() {
  return (
    <motion.span
      animate={{ opacity: [1, 0, 1] }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      className="inline-block w-0.5 h-4 bg-primary ml-0.5 rounded-full align-middle"
    />
  )
}

function MessageBubble({ msg, sessionId }: { msg: Message; sessionId: string }) {
  const approveWaitingTask = useChatStore((state) => state.approveWaitingTask)
  const isBusy = useChatStore(
    (state) => getActiveSession(state.sessions, state.activeSessionId)?.isBusy ?? false,
  )
  const isUser = msg.role === 'user'
  const isStreaming = msg.isStreaming ?? false
  const showStatusCard = !isUser && shouldShowStatusCard(msg.events)

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
      className={cn('flex gap-3 max-w-[90%]', isUser ? 'ml-auto flex-row-reverse' : 'mr-auto')}
    >
      <div className={cn(
        'w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-1',
        isUser
          ? 'bg-primary/20 border border-primary/20'
          : 'bg-white/5 border border-white/10'
      )}>
        {isUser
          ? <User className="w-4 h-4 text-primary/80" />
          : <Bot className="w-4 h-4 text-white/50" />
        }
      </div>

      <div className="flex flex-col gap-1.5 min-w-0">
        <div className={cn(
          'rounded-2xl px-4 py-3 text-sm leading-relaxed',
          isUser
            ? 'bg-primary/15 border border-primary/20 text-white/90 rounded-tr-sm'
            : 'bg-white/5 border border-white/8 text-white/80 rounded-tl-sm'
        )}>
          <span className="whitespace-pre-wrap break-words">{msg.content}</span>
          {isStreaming && msg.content.length > 0 && <StreamingCursor />}
          {!isUser && isStreaming && msg.content.length === 0 && (
            <LiveStageStrip events={msg.events} />
          )}
        </div>

        {!isUser && (
          <>
            <ThinkingTrace events={msg.events} isStreaming={isStreaming} />
            <ProgressUtteranceList events={msg.events} />
            {showStatusCard && (
              <TaskLoopStatusCard
                events={msg.events}
                isBusy={isBusy}
                onApprove={(taskId) => void approveWaitingTask(sessionId, msg.id, taskId)}
              />
            )}
          </>
        )}
      </div>
    </motion.div>
  )
}

export function ChatMessageList() {
  const { sessions, activeSessionId } = useChatStore()
  const activeSession = getActiveSession(sessions, activeSessionId)
  const messages = activeSession?.messages ?? []
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 scrollbar-thin scrollbar-thumb-white/10">
      {messages.length === 0 ? (
        <div className="h-full flex flex-col items-center justify-center gap-3 text-center">
          <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
            <Bot className="w-7 h-7 text-primary/60" />
          </div>
          <p className="text-white/30 text-sm max-w-[180px] leading-relaxed">
            Frag TRION etwas. Die KI antwortet im Stream.
          </p>
        </div>
      ) : (
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <MessageBubble key={msg.id} msg={msg} sessionId={activeSession?.id ?? ''} />
          ))}
        </AnimatePresence>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
