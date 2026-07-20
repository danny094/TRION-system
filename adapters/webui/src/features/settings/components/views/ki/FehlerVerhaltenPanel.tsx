import { cn } from '@/lib/utils'
import { DetailHeader } from './DetailHeader'

export type ErrorBehavior = 'retry' | 'ask' | 'abort'

interface Props { value: ErrorBehavior; onChange: (v: ErrorBehavior) => void; onBack: () => void }

const OPTIONS: { id: ErrorBehavior; label: string; desc: string }[] = [
  { id: 'retry', label: 'Begrenzt erneut versuchen', desc: 'TRION darf fehlgeschlagene Schritte kurz erneut versuchen und plant danach neu' },
  { id: 'ask',   label: 'Nach Fehlern nachfragen',   desc: 'TRION hält nach fehlgeschlagenen Schritten eher an und fragt nach' },
  { id: 'abort', label: 'Nach Fehlern abbrechen',    desc: 'TRION stoppt sichtbar statt nach Fehlern weiter zu replannen' },
]

export function FehlerVerhaltenPanel({ value, onChange, onBack }: Props) {
  return (
    <div className="flex flex-col gap-5">
      <DetailHeader
        title="Fehlerverhalten"
        subtitle="Die Einstellung steuert, wie TRION nach fehlgeschlagenen Schritten weiter eskaliert."
        onBack={onBack}
      />
      <div className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        {OPTIONS.map((o, i) => (
          <button
            key={o.id}
            type="button"
            onClick={() => onChange(o.id)}
            className={cn(
              'flex w-full items-center gap-3 py-3 text-left transition',
              i < OPTIONS.length - 1 && 'border-b border-white/5',
            )}
          >
            <div className={cn(
              'flex h-4 w-4 shrink-0 items-center justify-center rounded-full border',
              value === o.id ? 'border-purple-400/80' : 'border-white/25',
            )}>
              {value === o.id && (
                <div className="h-2 w-2 rounded-full bg-purple-400/90" />
              )}
            </div>
            <div>
              <div className={cn(
                'text-[12px] font-medium transition',
                value === o.id ? 'text-white/90' : 'text-white/65',
              )}>
                {o.label}
              </div>
              <div className="mt-0.5 text-[11px] text-white/38">{o.desc}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
