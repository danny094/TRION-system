import { Brain, History, MessageSquare, Search } from 'lucide-react'
import { useMemoryStore, type MemoryView } from '../state/memoryStore'
import { cn } from '@/lib/utils'

interface ViewOption {
  id: MemoryView
  label: string
  icon: typeof Brain
  hint: string
}

const VIEWS: ViewOption[] = [
  { id: 'recent', label: 'Zuletzt', icon: History, hint: 'Juengste Eintraege' },
  { id: 'search', label: 'Suchen', icon: Search, hint: 'Volltext, Semantik, Graph' },
  { id: 'conversations', label: 'Unterhaltungen', icon: MessageSquare, hint: 'Pro Conversation' },
]

export function MemorySidebar() {
  const view = useMemoryStore((s) => s.view)
  const setView = useMemoryStore((s) => s.setView)
  const selectConversation = useMemoryStore((s) => s.selectConversation)

  function switchTo(next: MemoryView) {
    setView(next)
    if (next !== 'conversations') selectConversation(null)
  }

  return (
    <div className="flex h-full w-[220px] shrink-0 flex-col border-r border-white/5 bg-black/15">
      <div className="px-5 pt-5 pb-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="rounded-xl border border-white/8 bg-white/5 p-1.5">
            <Brain className="w-4 h-4 text-white/75" />
          </div>
          <div>
            <div className="text-[12px] font-semibold text-white/88">Memory</div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-white/40">v 1.0</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-3 space-y-0.5">
        {VIEWS.map((option) => {
          const Icon = option.icon
          const isActive = view === option.id
          return (
            <button
              key={option.id}
              type="button"
              onClick={() => switchTo(option.id)}
              className={cn(
                'flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-[12px] transition',
                isActive
                  ? 'bg-white/8 text-white/92'
                  : 'text-white/65 hover:bg-white/5 hover:text-white/85',
              )}
            >
              <Icon className="w-3.5 h-3.5 shrink-0" />
              <span className="flex-1 text-left">{option.label}</span>
            </button>
          )
        })}
      </nav>

      <div className="border-t border-white/5 px-5 py-3 text-[10px] uppercase tracking-[0.16em] text-white/35">
        Live aus SQL Memory
      </div>
    </div>
  )
}
