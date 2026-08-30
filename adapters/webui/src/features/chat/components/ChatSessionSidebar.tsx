import { MessageSquarePlus, X, ChevronLeft, ChevronRight } from 'lucide-react'
import { useChatStore } from '../state/chatStore'
import { cn } from '@/lib/utils'
import { useTranslation } from '@/lib/i18n'

function formatTimestamp(value: string, locale: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat(locale, {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

interface ChatSessionSidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export function ChatSessionSidebar({ collapsed, onToggle }: ChatSessionSidebarProps) {
  const { sessions, activeSessionId, createSession, activateSession, closeSession } = useChatStore()
  const { locale, t } = useTranslation()

  // Collapsed: narrow strip with toggle + new-chat button + small dots per session
  if (collapsed) {
    return (
      <aside className="flex w-10 shrink-0 flex-col items-center gap-2 border-r border-white/8 bg-white/[0.03] py-3">
        <button
          type="button"
          onClick={onToggle}
          title={t('chat.showSessions')}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-white/45 transition hover:bg-white/8 hover:text-white/85"
        >
          <ChevronRight className="h-4 w-4" />
        </button>

        <button
          type="button"
          onClick={createSession}
          title={t('chat.newChat')}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-primary/25 bg-primary/12 text-primary transition hover:bg-primary/18"
        >
          <MessageSquarePlus className="h-4 w-4" />
        </button>

        <div className="mt-1 flex flex-1 flex-col items-center gap-1.5 overflow-y-auto py-1 scrollbar-thin scrollbar-thumb-white/10">
          {sessions.map((session) => {
            const isActive = session.id === activeSessionId
            return (
              <button
                key={session.id}
                type="button"
                onClick={() => activateSession(session.id)}
                title={session.title}
                className={cn(
                  'h-2 w-2 shrink-0 rounded-full transition',
                  isActive ? 'bg-primary scale-125' : 'bg-white/30 hover:bg-white/60'
                )}
              />
            )
          })}
        </div>
      </aside>
    )
  }

  // Expanded: full sidebar
  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-white/8 bg-white/[0.03]">
      <div className="border-b border-white/8 px-4 py-4 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-medium uppercase tracking-wider text-white/35">
            {t('chat.sessions')}
          </span>
          <button
            type="button"
            onClick={onToggle}
            title={t('chat.hideSessions')}
            className="flex h-6 w-6 items-center justify-center rounded-md text-white/40 transition hover:bg-white/8 hover:text-white/80"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
        </div>
        <button
          type="button"
          onClick={createSession}
          className="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-primary/25 bg-primary/12 px-4 py-3 text-sm font-medium text-primary transition hover:bg-primary/18"
        >
          <MessageSquarePlus className="h-4 w-4" />
          {t('chat.newChat')}
        </button>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto px-3 py-3 scrollbar-thin scrollbar-thumb-white/10">
        {sessions.map((session) => {
          const isActive = session.id === activeSessionId
          return (
            <div
              key={session.id}
              className={cn(
                'group rounded-2xl border transition',
                isActive
                  ? 'border-primary/25 bg-primary/12 shadow-[0_0_0_1px_rgba(64,200,255,0.12)]'
                  : 'border-white/8 bg-white/[0.025] hover:border-white/14 hover:bg-white/[0.05]',
              )}
            >
              <button
                type="button"
                onClick={() => activateSession(session.id)}
                className="flex w-full items-start gap-3 px-3 py-3 text-left"
              >
                <div className="mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full bg-primary/70" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-white/90">{session.title}</div>
                  <div className="mt-1 flex items-center gap-2 text-[11px] text-white/35">
                    <span>{t('chat.messages', { count: session.messages.length })}</span>
                    <span>·</span>
                    <span>{formatTimestamp(session.updatedAt, locale)}</span>
                    {session.isBusy ? (
                      <>
                        <span>·</span>
                        <span className="text-emerald-300/85">{t('chat.active')}</span>
                      </>
                    ) : null}
                  </div>
                </div>
              </button>

              {sessions.length > 1 ? (
                <div className="px-3 pb-3">
                  <button
                    type="button"
                    onClick={() => closeSession(session.id)}
                    className="inline-flex items-center gap-1 rounded-xl px-2 py-1 text-[11px] text-white/35 transition hover:bg-white/6 hover:text-white/65"
                  >
                    <X className="h-3.5 w-3.5" />
                    {t('chat.close')}
                  </button>
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    </aside>
  )
}
