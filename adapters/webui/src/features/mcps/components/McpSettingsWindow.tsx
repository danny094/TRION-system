import { useEffect, useState } from 'react'
import { Save } from 'lucide-react'
import { fetchMcpDetails, updateMcpConfig } from '@/features/mcps/api'
import type { McpDetails } from '@/lib/contracts/mcp'

interface McpSettingsWindowProps {
  mcpName: string
}

export function McpSettingsWindow({ mcpName }: McpSettingsWindowProps) {
  const [detail, setDetail] = useState<McpDetails | null>(null)
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    async function load() {
      setLoading(true)
      setError(null)
      setNotice(null)
      try {
        const next = await fetchMcpDetails(mcpName)
        if (!mounted) return
        setDetail(next)
        setDraft(next.rawConfig || '{}')
      } catch (err) {
        if (!mounted) return
        setError(err instanceof Error ? err.message : 'MCP settings could not be loaded.')
      } finally {
        if (mounted) setLoading(false)
      }
    }
    void load()
    return () => {
      mounted = false
    }
  }, [mcpName])

  async function handleSave() {
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const parsed = JSON.parse(draft) as Record<string, unknown>
      const response = await updateMcpConfig(mcpName, parsed)
      setDraft(JSON.stringify(response.config, null, 2))
      setNotice('Config saved and runtime reloaded.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Config could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="flex h-full items-center justify-center text-sm text-white/40">Loading MCP settings…</div>
  }

  if (!detail) {
    return <div className="flex h-full items-center justify-center text-sm text-white/40">No MCP details available.</div>
  }

  return (
    <div className="flex h-full flex-col text-sm">
      <header className="border-b border-white/8 px-6 py-4">
        <div className="text-[10px] uppercase tracking-[0.16em] text-white/35">host-managed settings</div>
        <h1 className="mt-2 text-[20px] font-semibold text-white/95">{detail.mcp.displayName}</h1>
        <p className="mt-1 text-[12px] text-white/50">
          {detail.editableConfig
            ? 'Generic MCP settings backed by the installer config endpoint.'
            : 'This MCP is currently read-only in the host settings view.'}
        </p>
      </header>

      {error && <div className="border-b border-rose-500/20 bg-rose-500/[0.06] px-6 py-2 text-xs text-rose-200">{error}</div>}
      {notice && <div className="border-b border-emerald-500/20 bg-emerald-500/[0.06] px-6 py-2 text-xs text-emerald-200">{notice}</div>}

      <div className="grid flex-1 grid-cols-[220px_1fr] gap-0 overflow-hidden">
        <aside className="border-r border-white/8 bg-white/[0.02] px-5 py-5">
          <div className="space-y-3">
            <MetaRow label="ID" value={detail.mcp.name} mono />
            <MetaRow label="Version" value={detail.mcp.version || '—'} mono />
            <MetaRow label="Transport" value={detail.mcp.transport} mono />
            <MetaRow label="Status" value={detail.mcp.online ? 'online' : 'offline'} />
            <MetaRow label="Tools" value={String(detail.mcp.toolsCount)} mono />
          </div>
        </aside>

        <main className="flex min-h-0 flex-col">
          <div className="flex-1 p-5">
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              readOnly={!detail.editableConfig || saving}
              spellCheck={false}
              className="h-full min-h-[320px] w-full resize-none rounded-2xl border border-white/8 bg-black/20 p-4 font-mono text-[12px] text-white/85 outline-none"
            />
          </div>
          <footer className="flex items-center justify-between border-t border-white/8 px-5 py-3">
            <span className="text-[11px] text-white/40">
              {detail.editableConfig ? 'Changes are written back to the MCP manifest/config.' : 'Read-only MCP configuration.'}
            </span>
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={!detail.editableConfig || saving}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary/85 px-3 py-1.5 text-[11px] font-medium text-black transition hover:bg-primary disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Save className="h-3.5 w-3.5" />
              Save
            </button>
          </footer>
        </main>
      </div>
    </div>
  )
}

function MetaRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.14em] text-white/35">{label}</div>
      <div className={`mt-1 text-[12px] text-white/80 ${mono ? 'font-mono' : ''}`}>{value}</div>
    </div>
  )
}
