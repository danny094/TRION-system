import { ChevronRight, ChevronLeft } from 'lucide-react'
import { PROVIDER_META, getProviderMeta } from './providerMeta'
import type { ModelRole } from '@/features/settings/api'

interface Props {
  role: ModelRole | 'EMBEDDING'
  label: string
  providers: string[]
  onSelect: (providerId: string) => void
  onBack: () => void
}

export function ProviderSelectView({ role: _role, label, providers, onSelect, onBack }: Props) {
  const list = providers.length > 0
    ? providers.map((id) => getProviderMeta(id))
    : PROVIDER_META

  return (
    <div className="flex flex-col gap-5">
      <header>
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1 text-[12px] text-primary transition hover:opacity-80"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Modelle
        </button>
        <h1 className="mt-3 text-[22px] font-semibold leading-tight text-white/95">{label}</h1>
        <p className="mt-1 text-[12px] text-white/55">
          Wähle die Plattform, von der du das Modell laden möchtest.
        </p>
      </header>

      <div className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
        {list.map((meta, idx) => (
          <div key={meta.id}>
            {idx > 0 && <div className="mx-4 border-t border-white/[0.04]" />}
            <button
              type="button"
              onClick={() => onSelect(meta.id)}
              className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[0.03] active:bg-white/[0.05]"
            >
              {meta.iconUrl ? (
                <img
                  src={meta.iconUrl}
                  alt={meta.label}
                  className="h-8 w-8 shrink-0 rounded-xl object-contain bg-white/8 p-1"
                />
              ) : (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/8 text-[11px] font-bold text-white/60">
                  {meta.label.slice(0, 2).toUpperCase()}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-medium text-white/85">{meta.label}</div>
                {meta.description && (
                  <div className="mt-0.5 text-[11px] text-white/40">{meta.description}</div>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1 text-[12px] text-white/40">
                Modelle
                <ChevronRight className="h-3.5 w-3.5 text-white/25" />
              </div>
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
