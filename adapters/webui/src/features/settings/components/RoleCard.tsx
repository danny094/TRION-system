import { Loader2, Save } from 'lucide-react'
import {
  ROLE_CONFIGS,
  SOURCE_LABELS,
  dedupeModelNames,
  visibleModelsForProvider,
  type RoleState,
} from '@/features/settings/providerSettingsHelpers'
import type { ModelCatalogEntry, ProviderId } from '@/features/settings/api'

interface RoleCardProps {
  config: typeof ROLE_CONFIGS[number]
  roleState: RoleState
  providers: ProviderId[]
  uniqueModels: string[]
  models: ModelCatalogEntry[]
  showAllOpenRouter: boolean
  dirty: boolean
  saving: boolean
  onUpdate: (patch: Partial<RoleState>) => void
  onSave: () => void
  onToggleOpenRouter: () => void
}

export function RoleCard(p: RoleCardProps) {
  return (
    <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-white/80">{p.config.label}</h3>
            <SourceBadge source={p.roleState.providerSourceKind} />
            <SourceBadge source={p.roleState.modelSourceKind} />
          </div>
          <p className="mt-1 text-[12px] text-white/45">{p.config.description}</p>
        </div>
        <button
          type="button"
          onClick={p.onSave}
          disabled={!p.dirty || p.saving || !p.roleState.provider || !p.roleState.model}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary/20 px-3 py-1.5 text-[11px] font-medium text-primary transition hover:bg-primary/30 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {p.saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
          Speichern
        </button>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <SelectField
          label="Provider"
          value={p.roleState.provider}
          options={p.providers}
          onChange={(provider) => {
            const nextModels = dedupeModelNames(
              visibleModelsForProvider(
                provider as ProviderId,
                p.models.filter((e) => e.provider === provider),
                p.showAllOpenRouter,
                p.roleState.model,
              ),
            )
            const nextModel = nextModels.includes(p.roleState.model)
              ? p.roleState.model
              : (nextModels[0] ?? '')
            p.onUpdate({ provider, model: nextModel })
          }}
        />
        <SelectField
          label="Modell"
          value={p.roleState.model}
          options={p.uniqueModels}
          onChange={(model) => p.onUpdate({ model })}
        />
      </div>

      {p.roleState.provider === 'openrouter' && (
        <div className="mt-3 flex items-center justify-between rounded-xl border border-white/8 bg-black/15 px-3 py-2 text-[11px] text-white/55">
          <span>Standardmäßig zeigen wir nur eine kuratierte OpenRouter-Auswahl.</span>
          <button
            type="button"
            onClick={p.onToggleOpenRouter}
            className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-0.5 text-[10px] uppercase tracking-[0.14em] text-white/70 transition hover:bg-white/[0.08]"
          >
            {p.showAllOpenRouter ? 'Empfohlene' : 'Alle Modelle'}
          </button>
        </div>
      )}

      <div className="mt-3 grid gap-2 text-[11px] md:grid-cols-2">
        <MiniCard label="Aktiver Stand" primary={p.roleState.sourceProvider || '—'} secondary={p.roleState.sourceModel || '—'} />
        <MiniCard label="Verfügbare Modelle" primary={String(p.uniqueModels.length)} secondary={p.roleState.provider} />
      </div>
    </section>
  )
}

interface SelectFieldProps { label: string; value: string; options: string[]; onChange: (v: string) => void }

function SelectField({ label, value, options, onChange }: SelectFieldProps) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[10px] uppercase tracking-[0.14em] text-white/35">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[12px] text-white/90 outline-none transition focus:border-primary/50"
      >
        {options.map((o) => (
          <option key={o} value={o} className="bg-zinc-950">{o}</option>
        ))}
      </select>
    </label>
  )
}

function MiniCard({ label, primary, secondary }: { label: string; primary: string; secondary: string }) {
  return (
    <div className="rounded-xl border border-white/8 bg-black/15 px-3 py-2">
      <div className="text-[10px] uppercase tracking-[0.14em] text-white/30">{label}</div>
      <div className="mt-1 text-white/75">{primary}</div>
      <div className="mt-0.5 text-white/45">{secondary}</div>
    </div>
  )
}

function SourceBadge({ source }: { source: string }) {
  const label = SOURCE_LABELS[source] ?? source ?? 'Unbekannt'
  return (
    <span className="rounded-full border border-white/10 bg-white/[0.04] px-1.5 py-0.5 text-[9px] uppercase tracking-[0.14em] text-white/50">
      {label}
    </span>
  )
}
