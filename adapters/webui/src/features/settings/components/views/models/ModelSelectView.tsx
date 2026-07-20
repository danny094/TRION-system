import { ChevronLeft, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getProviderMeta } from './providerMeta'
import type { ModelCatalogEntry, ModelRole } from '@/features/settings/api'

const MODEL_DESCRIPTIONS: Record<string, string> = {
  'deepseek-r1:8b':      'Smarte Reasoning-Engine für lokalen Einsatz',
  'llama3:latest':       'Metas Allrounder-Modell',
  'mistral:latest':      'Schnelles europäisches Open-Source-Modell',
  'qwen2.5-coder:7b':   'Exzellente Codegenerierung direkt lokal',
  'gpt-4o':              'Leistungsstarkes Multimodal-Modell von OpenAI',
  'gpt-4o-mini':         'Schnelle, günstige GPT-4o Variante',
  'claude-3-5-sonnet':   'Anthropics bestes Allround-Modell',
  'text-embedding-3-small': 'Kompaktes Embedding-Modell von OpenAI',
  'text-embedding-3-large': 'Hochpräzises Embedding-Modell von OpenAI',
}

interface Props {
  role: ModelRole | 'EMBEDDING'
  providerId: string
  providerLabel: string
  backLabel: string
  models: ModelCatalogEntry[]
  activeModel: string
  saving: boolean
  onSelect: (model: string) => void
  onBack: () => void
}

export function ModelSelectView({
  role: _role, providerId, providerLabel: _providerLabel, backLabel,
  models, activeModel, saving, onSelect, onBack,
}: Props) {
  const meta = getProviderMeta(providerId)
  const filtered = models.filter((m) => m.provider === providerId)

  return (
    <div className="flex flex-col gap-5">
      <header>
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1 text-[12px] text-primary transition hover:opacity-80"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          {backLabel}
        </button>
        <h1 className="mt-3 text-[22px] font-semibold leading-tight text-white/95">
          {meta.label || meta.id} Modelle
        </h1>
        <p className="mt-1 text-[12px] text-white/55">
          Verfügbare Modelle von deiner Instanz.
        </p>
      </header>

      {saving && (
        <div className="flex items-center gap-2 rounded-xl border border-white/8 bg-white/[0.02] px-4 py-2.5 text-[12px] text-white/55">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Wird gespeichert…
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="rounded-2xl border border-white/6 bg-white/[0.02] px-4 py-10 text-center text-[12px] text-white/30">
          Keine Modelle für diesen Provider verfügbar.
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
          {filtered.map((model, idx) => {
            const isActive = model.name === activeModel
            const desc = MODEL_DESCRIPTIONS[model.name] ?? model.category ?? ''
            return (
              <div key={model.name}>
                {idx > 0 && <div className="mx-4 border-t border-white/[0.04]" />}
                <button
                  type="button"
                  onClick={() => onSelect(model.name)}
                  className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-white/[0.03]"
                >
                  <div className="min-w-0 flex-1">
                    <div className={cn(
                      'text-[13px] font-medium',
                      isActive ? 'text-primary' : 'text-white/85',
                    )}>
                      {model.name}
                    </div>
                    {desc && (
                      <div className="mt-0.5 text-[11px] text-white/40">{desc}</div>
                    )}
                  </div>
                  <RadioDot active={isActive} />
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function RadioDot({ active }: { active: boolean }) {
  return (
    <div className={cn(
      'h-5 w-5 shrink-0 rounded-full border-2 transition-colors flex items-center justify-center',
      active
        ? 'border-primary bg-primary'
        : 'border-white/20 bg-transparent',
    )}>
      {active && <div className="h-2 w-2 rounded-full bg-white" />}
    </div>
  )
}
