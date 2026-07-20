import { useMemo, useState } from 'react'
import { Search, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { McpSummary } from '@/lib/contracts/mcp'

interface AllViewProps {
  items: McpSummary[]
  saving: boolean
  onToggle: (name: string) => void
}

type StatusFilter = 'installed' | 'online' | 'offline'

export function AllView({ items, saving, onToggle }: AllViewProps) {
  const [filter, setFilter] = useState<StatusFilter>('installed')
  const [search, setSearch] = useState('')

  const onlineCount = useMemo(() => items.filter((m) => m.enabled && m.online).length, [items])
  const offlineCount = items.length - onlineCount

  const filtered = useMemo(() => {
    const base =
      filter === 'online'
        ? items.filter((m) => m.enabled && m.online)
        : filter === 'offline'
          ? items.filter((m) => !m.enabled || !m.online)
          : items
    const q = search.trim().toLowerCase()
    if (!q) return base
    return base.filter(
      (m) => m.name.toLowerCase().includes(q) || m.description.toLowerCase().includes(q),
    )
  }, [items, filter, search])

  return (
    <div className="flex h-full flex-col gap-5">
      <header className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">
            {items.length} {items.length === 1 ? 'server' : 'servers'}
          </div>
          <h1 className="mt-2 text-[22px] font-semibold leading-tight text-white/95">
            All MCPs
          </h1>
        </div>
        <SearchInput value={search} onChange={setSearch} />
      </header>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FilterChip label="Installed" count={items.length} active={filter === 'installed'} onClick={() => setFilter('installed')} tint="emerald" />
          <FilterChip label="Online"    count={onlineCount}    active={filter === 'online'}    onClick={() => setFilter('online')} />
          <FilterChip label="Offline"   count={offlineCount}   active={filter === 'offline'}   onClick={() => setFilter('offline')} />
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-full border border-white/8 bg-white/[0.02] px-3 py-1 text-[11px] text-white/55 transition hover:bg-white/[0.04] hover:text-white/85"
        >
          <span className="text-white/40">Sort:</span>
          <span>Recent</span>
          <ChevronDown className="h-3 w-3" />
        </button>
      </div>

      <div className="flex-1 overflow-hidden rounded-2xl border border-white/6 bg-white/[0.015]">
        <Table items={filtered} saving={saving} onToggle={onToggle} empty={items.length === 0} />
      </div>
    </div>
  )
}

interface SearchInputProps { value: string; onChange: (v: string) => void }

function SearchInput({ value, onChange }: SearchInputProps) {
  return (
    <div className="flex items-center gap-2 rounded-full border border-white/8 bg-white/[0.03] px-3 py-1.5 w-56">
      <Search className="h-3.5 w-3.5 shrink-0 text-white/35" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search…"
        className="flex-1 bg-transparent text-[12px] text-white/85 placeholder:text-white/30 focus:outline-none"
      />
      <kbd className="rounded bg-white/8 px-1 py-0.5 text-[9px] text-white/45">⌘K</kbd>
    </div>
  )
}

interface FilterChipProps {
  label: string; count: number; active: boolean; onClick: () => void; tint?: 'emerald'
}

function FilterChip({ label, count, active, onClick, tint }: FilterChipProps) {
  const activeBg = tint === 'emerald'
    ? 'border-emerald-500/25 bg-emerald-500/[0.08] text-emerald-200'
    : 'border-white/12 bg-white/[0.06] text-white/85'
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] transition',
        active ? activeBg : 'border-white/8 bg-transparent text-white/50 hover:bg-white/[0.03] hover:text-white/80',
      )}
    >
      <span>{label}</span>
      <span className="tabular-nums text-white/45">{count}</span>
    </button>
  )
}

interface TableProps { items: McpSummary[]; saving: boolean; onToggle: (n: string) => void; empty: boolean }

function Table({ items, saving, onToggle, empty }: TableProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="grid shrink-0 grid-cols-[1fr_140px_90px_60px] gap-4 border-b border-white/6 px-4 py-2.5 text-[10px] uppercase tracking-[0.14em] text-white/35">
        <span>Server</span>
        <span>Status</span>
        <span>Size</span>
        <span className="text-right">Enabled</span>
      </div>
      {empty ? (
        <div className="flex-1 px-5 py-10 text-center text-[12px] text-white/35">No MCPs installed yet.</div>
      ) : items.length === 0 ? (
        <div className="flex-1 px-5 py-10 text-center text-[12px] text-white/35">No servers match the filter.</div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {items.map((mcp) => <Row key={mcp.name} mcp={mcp} saving={saving} onToggle={() => onToggle(mcp.name)} />)}
        </div>
      )}
    </div>
  )
}

function Row({ mcp, saving, onToggle }: { mcp: McpSummary; saving: boolean; onToggle: () => void }) {
  const online = mcp.enabled && mcp.online
  return (
    <div className="grid grid-cols-[1fr_140px_90px_60px] items-center gap-4 border-b border-white/4 px-4 py-2.5 last:border-b-0 transition hover:bg-white/[0.02]">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-6 w-6 shrink-0 items-center justify-center overflow-hidden rounded-md bg-gradient-to-br from-white/15 to-white/5">
          {mcp.iconUrl ? (
            <img src={mcp.iconUrl} alt={mcp.displayName} className="h-full w-full object-cover" />
          ) : null}
        </div>
        <div className="min-w-0">
          <div className="truncate font-mono text-[12px] text-white/90">{mcp.displayName}</div>
          <div className="truncate text-[11px] text-white/40">{mcp.description || `${mcp.toolsCount} tools`}</div>
        </div>
      </div>
      <div className="flex items-center gap-1.5 text-[11px]">
        <span className={cn('h-1.5 w-1.5 rounded-full', online ? 'bg-emerald-400' : 'bg-white/25')} />
        <span className={online ? 'text-emerald-300/85' : 'text-white/50'}>{online ? 'online' : 'offline'}</span>
        <span className="text-white/25">·</span>
        <span className="font-mono text-[10px] uppercase text-white/45">{mcp.transport}</span>
      </div>
      <div className="font-mono text-[11px] text-white/45">{mcp.version || '—'}</div>
      <div className="flex justify-end">
        <button
          type="button"
          onClick={onToggle}
          disabled={saving}
          role="switch"
          aria-checked={mcp.enabled}
          className={cn(
            'relative h-4 w-7 shrink-0 rounded-full transition-colors duration-200 disabled:opacity-40',
            mcp.enabled ? 'bg-emerald-500/80' : 'bg-white/12',
          )}
        >
          <span className={cn(
            'absolute top-0.5 h-3 w-3 rounded-full bg-white shadow-sm transition-transform duration-200',
            mcp.enabled ? 'translate-x-3.5' : 'translate-x-0.5',
          )} />
        </button>
      </div>
    </div>
  )
}
