import { Bot, Circle } from 'lucide-react'
import { useChatStore } from '../state/chatStore'
import { getActiveSession } from '../lib/sessionSelectors'

export function ChatHeader() {
  const { sessions, activeSessionId } = useChatStore()
  const activeSession = getActiveSession(sessions, activeSessionId)
  const isBusy = activeSession?.isBusy ?? false

  return (
    <div className="flex items-center gap-3 px-5 py-4 border-b border-white/5 bg-white/3 shrink-0">
      {/* TRION Avatar */}
      <div className="relative">
        <div className="w-9 h-9 rounded-xl bg-primary/15 border border-primary/25 flex items-center justify-center">
          <Bot className="w-5 h-5 text-primary" />
        </div>
        {/* Online Indicator */}
        <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-background bg-emerald-400" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-white/90 leading-tight">
          {activeSession?.title ?? 'TRION'}
        </div>
        <div className="flex items-center gap-1.5 mt-0.5">
          <Circle className="w-1.5 h-1.5 fill-emerald-400 text-emerald-400" />
          <span className="text-[11px] text-emerald-400/80 font-medium">
            {isBusy ? 'Denkt nach…' : 'Bereit'}
          </span>
        </div>
      </div>

      {activeSession ? (
        <div className="hidden text-right text-[11px] text-white/30 md:block">
          <div>{activeSession.messages.length} Nachrichten</div>
          <div className="font-mono text-[10px] text-white/20">{activeSession.conversationId}</div>
        </div>
      ) : null}
    </div>
  )
}
