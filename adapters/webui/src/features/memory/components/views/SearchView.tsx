import { useState } from 'react'
import { LoaderCircle, Search } from 'lucide-react'
import { searchMemory } from '../../api'
import type { SearchHit, SearchMode } from '../../contracts'
import { useMemoryStore } from '../../state/memoryStore'
import { cn } from '@/lib/utils'

const MODES: { id: SearchMode; label: string; hint: string }[] = [
  { id: 'fts', label: 'Volltext', hint: 'schnell, sucht in Worten' },
  { id: 'semantic', label: 'Semantisch', hint: 'sucht in Bedeutung' },
  { id: 'graph', label: 'Graph', hint: 'sucht in Verbindungen' },
]

export function SearchView() {
  const query = useMemoryStore((s) => s.searchQuery)
  const mode = useMemoryStore((s) => s.searchMode)
  const setQuery = useMemoryStore((s) => s.setSearchQuery)
  const setMode = useMemoryStore((s) => s.setSearchMode)
  const [hits, setHits] = useState<SearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastSearchedMode, setLastSearchedMode] = useState<SearchMode | null>(null)

  async function runSearch() {
    const trimmed = query.trim()
    if (!trimmed) {
      setHits([])
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const response = await searchMemory({ query: trimmed, mode, limit: 30 })
      setHits(response.hits ?? [])
      setLastSearchedMode(response.mode)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Suche fehlgeschlagen')
      setHits([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="px-8 py-7">
      <div>
        <div className="text-[10px] uppercase tracking-[0.22em] text-white/40">Memory</div>
        <h1 className="mt-1 text-[22px] font-semibold text-white/92">Suchen</h1>
        <p className="mt-1 text-[12px] text-white/55">Drei Suchmodi gegen das gleiche Memory.</p>
      </div>

      <div className="mt-6 flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') void runSearch()
            }}
            placeholder="Suchbegriff..."
            className="w-full rounded-xl border border-white/10 bg-white/5 py-2 pl-9 pr-3 text-[13px] text-white/85 placeholder:text-white/35 focus:border-white/20 focus:outline-none"
          />
        </div>
        <button
          type="button"
          onClick={() => void runSearch()}
          disabled={loading || !query.trim()}
          className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/8 px-4 py-2 text-[12px] text-white/85 hover:bg-white/12 disabled:opacity-40"
        >
          {loading ? <LoaderCircle className="w-3.5 h-3.5 animate-spin" /> : null}
          Suchen
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {MODES.map((option) => (
          <button
            key={option.id}
            type="button"
            onClick={() => setMode(option.id)}
            className={cn(
              'rounded-full border px-3 py-1 text-[11px] transition',
              mode === option.id
                ? 'border-white/15 bg-white/10 text-white/90'
                : 'border-white/5 bg-white/[0.02] text-white/55 hover:bg-white/5',
            )}
            title={option.hint}
          >
            {option.label}
          </button>
        ))}
        <span className="text-[10px] text-white/35 self-center ml-2">{MODES.find((entry) => entry.id === mode)?.hint}</span>
      </div>

      {error ? (
        <div className="mt-5 rounded-2xl border border-rose-400/25 bg-rose-500/10 px-4 py-3 text-[12px] text-rose-100/85">
          {error}
        </div>
      ) : null}

      <div className="mt-6 space-y-2.5">
        {hits.length === 0 && lastSearchedMode ? (
          <div className="rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-8 text-center text-[12px] text-white/45">
            Keine Treffer fuer "{query}".
          </div>
        ) : (
          hits.map((hit, index) => (
            <div
              key={`${hit.id ?? index}-${hit.source}`}
              className="rounded-2xl border border-white/6 bg-white/[0.02] px-4 py-3 transition hover:border-white/10 hover:bg-white/[0.035]"
            >
              <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-white/40">
                <span>{hit.source}</span>
                {typeof hit.score === 'number' ? <span>score {hit.score.toFixed(2)}</span> : null}
                {hit.conversation_id ? <span className="font-mono truncate max-w-[200px]">{hit.conversation_id}</span> : null}
              </div>
              <div className="mt-2 whitespace-pre-wrap break-words text-[13px] leading-relaxed text-white/82">
                {hit.content}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
