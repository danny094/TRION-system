import { useEffect, useState } from 'react'
import { ArrowLeft, ChevronRight, LoaderCircle, RotateCw } from 'lucide-react'
import {
  deleteMemory,
  fetchConversationEntries,
  fetchConversationPolicy,
  fetchConversations,
} from '../../api'
import type { ConversationPolicy, ConversationSummary, MemoryEntry } from '../../contracts'
import { useMemoryStore } from '../../state/memoryStore'
import { MemoryEntryItem } from '../MemoryEntryItem'
import { ForgetConfirmModal } from '../ForgetConfirmModal'
import { PrivacyBadge } from '../PrivacyBadge'

function formatTime(value?: string): string {
  if (!value) return ''
  try {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return value
  }
}

export function ConversationsView() {
  const selectedId = useMemoryStore((s) => s.selectedConversationId)
  const selectConversation = useMemoryStore((s) => s.selectConversation)

  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [loadingList, setLoadingList] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [policy, setPolicy] = useState<ConversationPolicy | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<MemoryEntry | null>(null)
  const [deleting, setDeleting] = useState(false)

  async function reloadList() {
    setLoadingList(true)
    setError(null)
    try {
      setConversations(await fetchConversations(100))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Laden fehlgeschlagen')
    } finally {
      setLoadingList(false)
    }
  }

  async function reloadDetail(conversationId: string) {
    setLoadingDetail(true)
    setError(null)
    try {
      const [next, nextPolicy] = await Promise.all([
        fetchConversationEntries(conversationId, 100),
        fetchConversationPolicy(conversationId),
      ])
      setEntries(next)
      setPolicy(nextPolicy)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Detail-Laden fehlgeschlagen')
    } finally {
      setLoadingDetail(false)
    }
  }

  useEffect(() => {
    if (!selectedId) {
      void reloadList()
    }
  }, [selectedId])

  useEffect(() => {
    if (selectedId) void reloadDetail(selectedId)
  }, [selectedId])

  async function confirmDelete() {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await deleteMemory(pendingDelete.id)
      setEntries((current) => current.filter((entry) => entry.id !== pendingDelete.id))
      setPendingDelete(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Loeschen fehlgeschlagen')
    } finally {
      setDeleting(false)
    }
  }

  if (selectedId) {
    return (
      <div className="px-8 py-7">
        <button
          type="button"
          onClick={() => selectConversation(null)}
          className="inline-flex items-center gap-1 text-[11px] text-white/55 hover:text-white/85"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Zurueck zu Unterhaltungen
        </button>
        <div className="mt-3 flex items-end justify-between gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] text-white/40">Conversation</div>
            <h1 className="mt-1 break-all text-[18px] font-semibold text-white/92 font-mono">{selectedId}</h1>
          </div>
          {policy ? <PrivacyBadge badge={policy.badge} /> : null}
        </div>

        {error ? (
          <div className="mt-5 rounded-2xl border border-rose-400/25 bg-rose-500/10 px-4 py-3 text-[12px] text-rose-100/85">{error}</div>
        ) : null}

        <div className="mt-6 space-y-2.5">
          {loadingDetail ? (
            <div className="rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-8 text-center text-[12px] text-white/45">Laedt...</div>
          ) : entries.length === 0 ? (
            <div className="rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-8 text-center text-[12px] text-white/45">Keine Eintraege.</div>
          ) : (
            entries.map((entry) => (
              <MemoryEntryItem
                key={entry.id}
                entry={entry}
                onDelete={(id) => {
                  const found = entries.find((item) => item.id === id) ?? null
                  setPendingDelete(found)
                }}
              />
            ))
          )}
        </div>

        <ForgetConfirmModal
          open={pendingDelete !== null}
          description={pendingDelete?.content?.slice(0, 200) ?? ''}
          onConfirm={confirmDelete}
          onCancel={() => setPendingDelete(null)}
          busy={deleting}
        />
      </div>
    )
  }

  return (
    <div className="px-8 py-7">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="text-[10px] uppercase tracking-[0.22em] text-white/40">Memory</div>
          <h1 className="mt-1 text-[22px] font-semibold text-white/92">Unterhaltungen</h1>
          <p className="mt-1 text-[12px] text-white/55">Eine Liste aller Unterhaltungen, die TRION sich gemerkt hat.</p>
        </div>
        <button
          type="button"
          onClick={reloadList}
          disabled={loadingList}
          className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] text-white/75 hover:bg-white/10 disabled:opacity-40"
        >
          {loadingList ? <LoaderCircle className="w-3.5 h-3.5 animate-spin" /> : <RotateCw className="w-3.5 h-3.5" />}
          Neu laden
        </button>
      </div>

      {error ? (
        <div className="mt-5 rounded-2xl border border-rose-400/25 bg-rose-500/10 px-4 py-3 text-[12px] text-rose-100/85">{error}</div>
      ) : null}

      <div className="mt-6 space-y-1.5">
        {loadingList && conversations.length === 0 ? (
          <div className="rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-8 text-center text-[12px] text-white/45">Laedt...</div>
        ) : conversations.length === 0 ? (
          <div className="rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-8 text-center text-[12px] text-white/45">Keine Unterhaltungen gespeichert.</div>
        ) : (
          conversations.map((conv) => (
            <button
              key={conv.conversation_id}
              type="button"
              onClick={() => selectConversation(conv.conversation_id)}
              className="group w-full rounded-2xl border border-white/6 bg-white/[0.02] px-4 py-3 text-left transition hover:border-white/10 hover:bg-white/[0.035]"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="truncate font-mono text-[13px] text-white/82">{conv.conversation_id}</div>
                  <div className="mt-1 flex gap-3 text-[10px] uppercase tracking-[0.16em] text-white/40">
                    {typeof conv.entry_count === 'number' ? <span>{conv.entry_count} Eintraege</span> : null}
                    {conv.last_activity_at ? <span>{formatTime(conv.last_activity_at)}</span> : null}
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-white/30 group-hover:text-white/60" />
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
