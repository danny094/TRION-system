import { ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ModelRole } from '@/features/settings/api'
import type { RoleState } from '@/features/settings/providerSettingsHelpers'

export type ModelsDrillTarget =
  | { kind: 'provider-select'; role: ModelRole | 'EMBEDDING'; label: string }

interface RowConfig {
  role: ModelRole | 'EMBEDDING'
  label: string
  description: string
  tint: string
  emblem: string
}

const ROWS: RowConfig[] = [
  { role: 'OUTPUT',    label: 'Output-Modell',    description: 'Gibt die finalen Antworten im Editor aus',         tint: '#5b6af8', emblem: '◈' },
  { role: 'CONTROL',  label: 'Control-Modell',   description: 'Gesteuert durch Simple-Modus',                     tint: '#c05555', emblem: '⬡' },
  { role: 'THINKING', label: 'Thinking-Modell',  description: 'Gesteuert durch Simple-Modus',                     tint: '#3d9e7a', emblem: '◎' },
  { role: 'EMBEDDING',label: 'Embedding-Modell', description: 'Modell für semantische Textrepräsentationen',      tint: '#c07830', emblem: '◉' },
]

interface Props {
  roles: Record<ModelRole, RoleState>
  simpleMode: boolean
  embeddingEnabled: boolean
  embeddingProvider: string
  embeddingModel: string
  onToggleSimple: () => void
  onToggleEmbedding: () => void
  onDrill: (target: ModelsDrillTarget) => void
}

export function ModelsOverview({
  roles, simpleMode, embeddingEnabled,
  embeddingProvider: _embeddingProvider, embeddingModel,
  onToggleSimple, onToggleEmbedding, onDrill,
}: Props) {
  function modelLabel(role: ModelRole | 'EMBEDDING') {
    if (role === 'EMBEDDING') return embeddingModel || '—'
    return roles[role]?.model || '—'
  }

  function isLocked(role: ModelRole | 'EMBEDDING') {
    return simpleMode && (role === 'CONTROL' || role === 'THINKING')
  }

  return (
    <div className="flex flex-col gap-5">
      <header>
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">
          Voreinstellungen
        </div>
        <h1 className="mt-2 text-[22px] font-semibold leading-tight text-white/95">
          Modelle-Konfiguration
        </h1>
        <p className="mt-2 text-[12px] text-white/55">
          Steuere die KI-Modelle für die verschiedenen Verarbeitungsebenen.
        </p>
      </header>

      {/* Layer-Sektion */}
      <div className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
        {/* Output */}
        <ModelRow
          config={ROWS[0]}
          valueLabel={modelLabel('OUTPUT')}
          locked={false}
          onClick={() => onDrill({ kind: 'provider-select', role: 'OUTPUT', label: 'Output-Provider' })}
        />

        <div className="mx-4 border-t border-white/[0.04]" />

        {/* Simple-Modus Toggle */}
        <div className="flex items-start justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-3">
            <div
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-[14px]"
              style={{ backgroundColor: '#5845c0' }}
            >
              <span className="text-white/90 text-[11px] font-bold">S</span>
            </div>
            <div>
              <div className="text-[13px] font-medium text-white/85">Simple-Modus</div>
              <div className="mt-0.5 text-[11px] text-white/40">
                Wählt für alle Layer das gleiche Modell
                {simpleMode && <span className="ml-1 text-white/30">(Mindestens output muss ausgewählt sein)</span>}
              </div>
            </div>
          </div>
          <Toggle enabled={simpleMode} onToggle={onToggleSimple} />
        </div>

        <div className="mx-4 border-t border-white/[0.04]" />

        {/* Control */}
        <ModelRow
          config={ROWS[1]}
          valueLabel={isLocked('CONTROL') ? modelLabel('OUTPUT') : modelLabel('CONTROL')}
          locked={isLocked('CONTROL')}
          lockedHint="Gesteuert durch Simple-Modus"
          onClick={() => !isLocked('CONTROL') && onDrill({ kind: 'provider-select', role: 'CONTROL', label: 'Control-Provider' })}
        />

        <div className="mx-4 border-t border-white/[0.04]" />

        {/* Thinking */}
        <ModelRow
          config={ROWS[2]}
          valueLabel={isLocked('THINKING') ? modelLabel('OUTPUT') : modelLabel('THINKING')}
          locked={isLocked('THINKING')}
          lockedHint="Gesteuert durch Simple-Modus"
          onClick={() => !isLocked('THINKING') && onDrill({ kind: 'provider-select', role: 'THINKING', label: 'Thinking-Provider' })}
        />
      </div>

      {/* Embedding-Sektion */}
      <div className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
        {/* Embedding Toggle */}
        <div className="flex items-start justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-3">
            <div
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl"
              style={{ backgroundColor: '#c07830' }}
            >
              <span className="text-white/90 text-[11px] font-bold">E</span>
            </div>
            <div>
              <div className="text-[13px] font-medium text-white/85">Embedding aktivieren</div>
              <div className="mt-0.5 text-[11px] text-white/40">Nutzt Vektorsuche für kontextbasierte Daten</div>
            </div>
          </div>
          <Toggle enabled={embeddingEnabled} onToggle={onToggleEmbedding} />
        </div>

        <div className="mx-4 border-t border-white/[0.04]" />

        {/* Embedding Model */}
        <ModelRow
          config={ROWS[3]}
          valueLabel={modelLabel('EMBEDDING')}
          locked={false}
          onClick={() => onDrill({ kind: 'provider-select', role: 'EMBEDDING', label: 'Embedding-Provider' })}
        />
      </div>

      <p className="text-[11px] text-white/25">
        Deaktiviert man das Embedding, wird ein Fallback auf reine Code-Bearbeitung angewendet.
      </p>
    </div>
  )
}

/* ── Sub-components ─────────────────────────────────────────── */

interface ModelRowProps {
  config: RowConfig
  valueLabel: string
  locked: boolean
  lockedHint?: string
  onClick: () => void
}

function ModelRow({ config, valueLabel, locked, lockedHint, onClick }: ModelRowProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={locked}
      className={cn(
        'flex w-full items-center gap-3 px-4 py-3 text-left transition-colors',
        locked
          ? 'cursor-default opacity-45'
          : 'hover:bg-white/[0.03] active:bg-white/[0.05]',
      )}
    >
      <div
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-white/80"
        style={{ backgroundColor: config.tint }}
      >
        <span className="text-[15px] leading-none">{config.emblem}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[13px] font-medium text-white/85">{config.label}</div>
        <div className="mt-0.5 text-[11px] text-white/40">
          {locked && lockedHint ? lockedHint : config.description}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1.5 text-[12px] text-white/45">
        <span className="max-w-[120px] truncate">{valueLabel}</span>
        {!locked && <ChevronRight className="h-3.5 w-3.5 text-white/30" />}
      </div>
    </button>
  )
}

interface ToggleProps { enabled: boolean; onToggle: () => void }

function Toggle({ enabled, onToggle }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={onToggle}
      className={cn(
        'relative h-6 w-11 shrink-0 rounded-full transition-colors duration-200',
        enabled ? 'bg-primary' : 'bg-white/15',
      )}
    >
      <span className={cn(
        'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform duration-200',
        enabled ? 'translate-x-5' : 'translate-x-0.5',
      )} />
    </button>
  )
}
