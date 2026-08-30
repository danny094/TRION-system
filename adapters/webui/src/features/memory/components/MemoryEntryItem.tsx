import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import type { MemoryEntry } from '../contracts'
import { cn } from '@/lib/utils'
import { useTranslation } from '@/lib/i18n'

interface MemoryEntryItemProps {
  entry: MemoryEntry
  onDelete?: (id: number) => Promise<void> | void
  onSelectConversation?: (id: string) => void
}

function formatTime(value: string | undefined, locale: string): string {
  if (!value) return ''
  try {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString(locale, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}

export function MemoryEntryItem({ entry, onDelete, onSelectConversation }: MemoryEntryItemProps) {
  const [isBusy, setIsBusy] = useState(false)
  const { locale, t } = useTranslation()
  const role = entry.role?.trim()
  const layer = entry.layer?.trim()
  const created = formatTime(entry.created_at, locale)

  async function handleDelete() {
    if (!onDelete || isBusy) return
    setIsBusy(true)
    try {
      await onDelete(entry.id)
    } finally {
      setIsBusy(false)
    }
  }

  return (
    <div className="group rounded-2xl border border-white/6 bg-white/[0.02] px-4 py-3 transition hover:border-white/10 hover:bg-white/[0.035]">
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-white/40">
            {role ? <span>{role}</span> : null}
            {layer ? <span>{layer}</span> : null}
            {created ? <span>{created}</span> : null}
            {entry.conversation_id ? (
              <button
                type="button"
                onClick={() => onSelectConversation?.(entry.conversation_id)}
                className={cn(
                  'truncate max-w-[200px] font-mono text-white/45 hover:text-white/75',
                  onSelectConversation ? 'cursor-pointer' : 'cursor-default',
                )}
              >
                {entry.conversation_id}
              </button>
            ) : null}
          </div>
          <div className="mt-2 whitespace-pre-wrap break-words text-[13px] leading-relaxed text-white/82">
            {entry.content}
          </div>
          {entry.tags ? (
            <div className="mt-2 text-[11px] text-white/45">{entry.tags}</div>
          ) : null}
        </div>
        {onDelete ? (
          <button
            type="button"
            onClick={handleDelete}
            disabled={isBusy}
            className="opacity-0 group-hover:opacity-100 transition rounded-lg border border-rose-400/25 bg-rose-500/10 px-2 py-1 text-rose-100/80 hover:bg-rose-500/20 disabled:opacity-30"
            title={t('memory.forget')}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        ) : null}
      </div>
    </div>
  )
}
