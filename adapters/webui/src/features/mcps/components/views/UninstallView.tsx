import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { McpSummary } from '@/lib/contracts/mcp'
import { ConfirmRemoveModal } from './ConfirmRemoveModal'

interface UninstallViewProps {
  items: McpSummary[]
  saving: boolean
  onRemove: (name: string) => void
}

export function UninstallView({ items, saving, onRemove }: UninstallViewProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [confirmName, setConfirmName] = useState<string | null>(null)
  const [confirmBatch, setConfirmBatch] = useState(false)

  const allSelected = items.length > 0 && selected.size === items.length

  function toggle(name: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  function toggleAll() {
    setSelected(allSelected ? new Set() : new Set(items.map((m) => m.name)))
  }

  function runBatch() {
    selected.forEach((name) => onRemove(name))
    setSelected(new Set())
    setConfirmBatch(false)
  }

  return (
    <div className="flex h-full flex-col gap-5">
      <header>
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">
          remove a server
        </div>
        <h1 className="mt-2 text-[22px] font-semibold leading-tight text-white/95">
          Uninstall MCP
        </h1>
        <p className="mt-2 text-[12px] text-white/55">
          Select one or more servers. Files and config are removed; the TRION runtime is reloaded.
        </p>
      </header>

      <div className="flex-1 overflow-hidden rounded-2xl border border-white/6 bg-white/[0.015]">
        <div className="grid shrink-0 grid-cols-[24px_1fr_120px_80px_40px] gap-3 border-b border-white/6 px-4 py-2.5 text-[10px] uppercase tracking-[0.14em] text-white/35">
          <Checkbox checked={allSelected} onChange={toggleAll} />
          <span>Server</span>
          <span>Installed</span>
          <span>Size</span>
          <span />
        </div>
        {items.length === 0 ? (
          <div className="px-5 py-10 text-center text-[12px] text-white/35">No MCPs installed.</div>
        ) : (
          <div className="overflow-y-auto">
            {items.map((mcp) => (
              <Row
                key={mcp.name}
                mcp={mcp}
                selected={selected.has(mcp.name)}
                onToggle={() => toggle(mcp.name)}
                onTrash={() => setConfirmName(mcp.name)}
                saving={saving}
              />
            ))}
          </div>
        )}
      </div>

      <FooterBar
        count={selected.size}
        onCancel={() => setSelected(new Set())}
        onRun={() => setConfirmBatch(true)}
        saving={saving}
      />

      {confirmName && (
        <ConfirmRemoveModal
          title="Remove this server?"
          subtitle={confirmName}
          onCancel={() => setConfirmName(null)}
          onConfirm={() => { onRemove(confirmName); setConfirmName(null) }}
        />
      )}
      {confirmBatch && (
        <ConfirmRemoveModal
          title="Remove selected servers?"
          subtitle={`${selected.size} servers will be deleted permanently.`}
          onCancel={() => setConfirmBatch(false)}
          onConfirm={runBatch}
        />
      )}
    </div>
  )
}

interface RowProps {
  mcp: McpSummary; selected: boolean; saving: boolean
  onToggle: () => void; onTrash: () => void
}

function Row({ mcp, selected, saving, onToggle, onTrash }: RowProps) {
  return (
    <div className={cn(
      'grid grid-cols-[24px_1fr_120px_80px_40px] items-center gap-3 border-b border-white/4 px-4 py-2.5 transition last:border-b-0',
      selected ? 'bg-rose-500/[0.05]' : 'hover:bg-white/[0.02]',
    )}>
      <Checkbox checked={selected} onChange={onToggle} tint={selected ? 'rose' : undefined} />
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
      <div className="font-mono text-[11px] text-white/45">—</div>
      <div className="font-mono text-[11px] text-white/45">—</div>
      <button
        type="button"
        onClick={onTrash}
        disabled={saving}
        className={cn(
          'flex h-7 w-7 items-center justify-center rounded-lg border transition disabled:opacity-40',
          selected
            ? 'border-rose-500/30 bg-rose-500/12 text-rose-300 hover:bg-rose-500/20'
            : 'border-white/8 bg-white/[0.02] text-white/40 hover:text-white/75 hover:bg-white/[0.06]',
        )}
        aria-label={`Remove ${mcp.name}`}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

function Checkbox({ checked, onChange, tint }: { checked: boolean; onChange: () => void; tint?: 'rose' }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      onClick={onChange}
      className={cn(
        'flex h-4 w-4 items-center justify-center rounded border transition',
        checked
          ? tint === 'rose'
            ? 'border-rose-400/60 bg-rose-500/35 text-white'
            : 'border-white/40 bg-white/15 text-white'
          : 'border-white/15 bg-transparent hover:border-white/30',
      )}
    >
      {checked && (
        <svg viewBox="0 0 12 12" className="h-2.5 w-2.5">
          <path d="M2 6l3 3 5-6" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
    </button>
  )
}

interface FooterProps { count: number; onCancel: () => void; onRun: () => void; saving: boolean }

function FooterBar({ count, onCancel, onRun, saving }: FooterProps) {
  const has = count > 0
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-white/6 bg-white/[0.015] px-4 py-2.5">
      <div className="flex items-center gap-2 text-[11px]">
        <span className={cn(
          'flex h-5 w-5 items-center justify-center rounded-md font-mono text-[10px] tabular-nums',
          has ? 'bg-rose-500/20 text-rose-200' : 'bg-white/6 text-white/45',
        )}>{count}</span>
        <span className={has ? 'text-white/70' : 'text-white/35'}>selected for removal</span>
      </div>
      <div className="flex items-center gap-2">
        <button type="button" onClick={onCancel} disabled={!has} className="rounded-lg px-3 py-1.5 text-[11px] text-white/65 transition hover:bg-white/5 hover:text-white/90 disabled:opacity-30">
          Cancel
        </button>
        <button
          type="button"
          onClick={onRun}
          disabled={!has || saving}
          className="rounded-lg bg-rose-500/85 px-3 py-1.5 text-[11px] font-medium text-white shadow-sm transition hover:bg-rose-400 disabled:cursor-not-allowed disabled:bg-rose-500/30 disabled:text-white/50"
        >
          Uninstall selected
        </button>
      </div>
    </div>
  )
}
