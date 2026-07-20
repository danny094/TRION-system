import { useEffect, useState } from 'react'
import { LoaderCircle, RotateCw } from 'lucide-react'
import { deleteMemory, fetchRecent } from '../../api'
import type { MemoryEntry } from '../../contracts'
import { useMemoryStore } from '../../state/memoryStore'
import { MemoryEntryItem } from '../MemoryEntryItem'
import { ForgetConfirmModal } from '../ForgetConfirmModal'

export function RecentView() {
  const selectConversation = useMemoryStore((s) => s.selectConversation)
  const setView = useMemoryStore((s) => s.setView)
  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<MemoryEntry | null>(null)
  const [deleting, setDeleting] = useState(false)

  async function reload() {
    setLoading(true)
    setError(null)
    try {
      const next = await fetchRecent(null, 50)
      setEntries(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Laden fehlgeschlagen')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void reload()
  }, [])

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

  function handleSelectConversation(id: string) {
    selectConversation(id)
    setView('conversations')
  }

  return (
    <div className="px-8 py-7">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="text-[10px] uppercase tracking-[0.22em] text-white/40">Memory</div>
          <h1 className="mt-1 text-[22px] font-semibold text-white/92">Zuletzt gemerkt</h1>
          <p className="mt-1 text-[12px] text-white/55">Die juengsten Eintraege ueber alle Unterhaltungen.</p>
        </div>
        <button
          type="button"
          onClick={reload}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] text-white/75 hover:bg-white/10 disabled:opacity-40"
        >
          {loading ? <LoaderCircle className="w-3.5 h-3.5 animate-spin" /> : <RotateCw className="w-3.5 h-3.5" />}
          Neu laden
        </button>
      </div>

      {error ? (
        <div className="mt-5 rounded-2xl border border-rose-400/25 bg-rose-500/10 px-4 py-3 text-[12px] text-rose-100/85">
          {error}
        </div>
      ) : null}

      <div className="mt-6 space-y-2.5">
        {loading && entries.length === 0 ? (
          <div className="rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-8 text-center text-[12px] text-white/45">
            Laedt...
          </div>
        ) : entries.length === 0 ? (
          <div className="rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-8 text-center text-[12px] text-white/45">
            Noch keine Erinnerungen.
          </div>
        ) : (
          entries.map((entry) => (
            <MemoryEntryItem
              key={entry.id}
              entry={entry}
              onDelete={(id) => {
                const found = entries.find((item) => item.id === id) ?? null
                setPendingDelete(found)
              }}
              onSelectConversation={handleSelectConversation}
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
