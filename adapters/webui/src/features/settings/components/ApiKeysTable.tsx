import { Trash2, Loader2 } from 'lucide-react'
import type { ApiKey } from '@/features/settings/apiKeysApi'

interface ApiKeysTableProps {
  keys: ApiKey[]
  loading: boolean
  deletingId: string | null
  onDelete: (id: string, name: string) => void
}

export function ApiKeysTable({ keys, loading, deletingId, onDelete }: ApiKeysTableProps) {
  return (
    <section className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
      <div className="grid grid-cols-12 gap-4 border-b border-white/6 px-4 py-2.5 text-[10px] font-medium uppercase tracking-[0.14em] text-white/35">
        <div className="col-span-4">Name</div>
        <div className="col-span-4">Schlüssel</div>
        <div className="col-span-4">Zuletzt geändert</div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center px-4 py-10 text-[12px] text-white/35">
          <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
          Keys werden geladen
        </div>
      ) : keys.length === 0 ? (
        <div className="px-4 py-10 text-center text-[12px] text-white/30">
          Noch keine Keys gespeichert. Füge deinen ersten Key oben hinzu.
        </div>
      ) : (
        <div className="divide-y divide-white/4">
          {keys.map((k) => (
            <Row key={k.id} apiKey={k} deleting={deletingId === k.id} onDelete={() => onDelete(k.id, k.name)} />
          ))}
        </div>
      )}
    </section>
  )
}

interface RowProps { apiKey: ApiKey; deleting: boolean; onDelete: () => void }

function Row({ apiKey, deleting, onDelete }: RowProps) {
  return (
    <div className="group grid grid-cols-12 items-center gap-4 px-4 py-2.5 transition-colors hover:bg-white/[0.02]">
      <div className="col-span-4 font-mono text-[11px] text-white/85">{apiKey.name}</div>
      <div className="col-span-4 font-mono text-[11px] tracking-widest text-white/40">{apiKey.masked_value}</div>
      <div className="col-span-3 text-[11px] text-white/35">{apiKey.last_modified}</div>
      <div className="col-span-1 flex justify-end opacity-0 transition-opacity group-hover:opacity-100">
        <button
          type="button"
          onClick={onDelete}
          disabled={deleting}
          className="rounded-md p-1 text-white/30 transition hover:bg-rose-500/10 hover:text-rose-300 disabled:opacity-50"
          title={`${apiKey.name} entfernen`}
          aria-label={`${apiKey.name} entfernen`}
        >
          {deleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
        </button>
      </div>
    </div>
  )
}
