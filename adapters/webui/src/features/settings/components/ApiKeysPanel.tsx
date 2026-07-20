import { useState, useEffect } from 'react'
import { Plus, Loader2, RefreshCw, Eye, EyeOff, CircleHelp } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ApiError } from '@/lib/api/client'
import { fetchApiKeys, addApiKey, deleteApiKey, type ApiKey } from '@/features/settings/apiKeysApi'
import { ApiKeyNamingHelp } from '@/features/settings/components/ApiKeyNamingHelp'
import { ApiKeysTable } from '@/features/settings/components/ApiKeysTable'

export function ApiKeysPanel() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [newValue, setNewValue] = useState('')
  const [showValue, setShowValue] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [adding, setAdding] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => { void load(true) }, [])

  async function load(initial = false) {
    if (initial) setLoading(true)
    else setRefreshing(true)
    setError(null)
    try {
      const res = await fetchApiKeys()
      setKeys(res.keys)
    } catch (err) {
      setError(apiErrorMessage(err, 'API-Keys konnten nicht geladen werden.'))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  async function handleAdd() {
    const name = newName.trim().toUpperCase()
    const value = newValue.trim()
    if (!name || !value) return
    setAdding(true)
    setError(null)
    setStatus(null)
    try {
      const added = await addApiKey({ name, value })
      setKeys((prev) => [added, ...prev])
      setNewName('')
      setNewValue('')
      setStatus(`„${added.name}" wurde gespeichert.`)
    } catch (err) {
      setError(apiErrorMessage(err, 'Key konnte nicht gespeichert werden.'))
    } finally {
      setAdding(false)
    }
  }

  async function handleDelete(id: string, name: string) {
    setDeletingId(id)
    setError(null)
    setStatus(null)
    try {
      await deleteApiKey(id)
      setKeys((prev) => prev.filter((k) => k.id !== id))
      setStatus(`„${name}" wurde entfernt.`)
    } catch (err) {
      setError(apiErrorMessage(err, 'Key konnte nicht gelöscht werden.'))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <header className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">Voreinstellungen</div>
          <div className="mt-2 flex items-center gap-2">
            <h1 className="text-[22px] font-semibold leading-tight text-white/95">API-Schlüssel</h1>
            <button
              type="button"
              onClick={() => setShowHelp((v) => !v)}
              className={cn(
                'inline-flex h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-white/45 transition hover:bg-white/[0.06] hover:text-white/85',
                showHelp && 'border-amber-400/30 bg-amber-400/10 text-amber-200',
              )}
              title="Welche Key-Namen werden gelesen?"
              aria-label="Welche Key-Namen werden gelesen?"
            >
              <CircleHelp className="h-3.5 w-3.5" />
            </button>
          </div>
          <p className="mt-2 text-[12px] text-white/55">
            Verwalte API-Keys für externe Provider. Werte werden verschlüsselt gespeichert.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load(false)}
          disabled={refreshing}
          className="inline-flex items-center gap-1.5 rounded-lg border border-white/8 bg-white/[0.03] px-3 py-1.5 text-[11px] text-white/70 transition hover:bg-white/[0.06] hover:text-white/95 disabled:opacity-50"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', refreshing && 'animate-spin')} />
          Aktualisieren
        </button>
      </header>

      {error && <Banner kind="error">{error}</Banner>}
      {status && !error && <Banner kind="success">{status}</Banner>}
      {showHelp && <ApiKeyNamingHelp />}

      <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-white/35">Neuen Key hinzufügen</div>
        <div className="mt-3 flex gap-2">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && void handleAdd()}
            placeholder="NAME (z.B. OPENAI_API_KEY)"
            className="w-1/3 rounded-xl border border-white/10 bg-black/20 px-3 py-2 font-mono text-[11px] text-white/85 outline-none transition placeholder:text-white/25 focus:border-primary/50"
          />
          <div className="relative flex-1">
            <input
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void handleAdd()}
              type={showValue ? 'text' : 'password'}
              placeholder="sk-…"
              className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 pr-9 font-mono text-[11px] text-white/85 outline-none transition placeholder:text-white/25 focus:border-primary/50"
            />
            <button
              type="button"
              onClick={() => setShowValue((v) => !v)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-white/30 transition-colors hover:text-white/65"
              title={showValue ? 'Verbergen' : 'Anzeigen'}
            >
              {showValue ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </button>
          </div>
          <button
            type="button"
            onClick={() => void handleAdd()}
            disabled={adding || !newName.trim() || !newValue.trim()}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-primary/20 px-3.5 py-2 text-[11px] font-medium text-primary transition hover:bg-primary/30 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {adding ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
            Hinzufügen
          </button>
        </div>
      </section>

      <ApiKeysTable keys={keys} loading={loading} deletingId={deletingId} onDelete={(id, name) => void handleDelete(id, name)} />
    </div>
  )
}

function Banner({ kind, children }: { kind: 'error' | 'success'; children: React.ReactNode }) {
  const cls = kind === 'error'
    ? 'border-rose-500/20 bg-rose-500/[0.06] text-rose-200'
    : 'border-emerald-500/20 bg-emerald-500/[0.06] text-emerald-200'
  return <div className={cn('rounded-2xl border px-4 py-2.5 text-[12px]', cls)}>{children}</div>
}

function apiErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const detail = typeof err.body?.detail === 'string' ? err.body.detail : ''
    return detail ? `${fallback} ${detail}` : fallback
  }
  if (err instanceof Error && err.message) return `${fallback} ${err.message}`
  return fallback
}
