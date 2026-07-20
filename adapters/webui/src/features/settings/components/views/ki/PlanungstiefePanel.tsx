import { cn } from '@/lib/utils'
import { DetailHeader } from './DetailHeader'

export type PlanningDepth = 'schnell' | 'normal' | 'gründlich' | 'unbegrenzt'

interface Props { value: PlanningDepth; onChange: (v: PlanningDepth) => void; onBack: () => void }

const OPTIONS: { id: PlanningDepth; label: string; hint: string }[] = [
  { id: 'schnell',      label: 'Schnell',      hint: 'Bis zu 3 Schritte — direkt und schnell' },
  { id: 'normal',       label: 'Normal',       hint: 'Bis zu 10 Schritte pro Task' },
  { id: 'gründlich',    label: 'Gründlich',    hint: 'Bis zu 25 Schritte für komplexe Aufgaben' },
  { id: 'unbegrenzt',   label: 'Unbegrenzt',   hint: 'Keine Begrenzung — TRION denkt so weit wie nötig' },
]

export function PlanungstiefePanel({ value, onChange, onBack }: Props) {
  const current = OPTIONS.find((o) => o.id === value)
  return (
    <div className="flex flex-col gap-5">
      <DetailHeader
        title="Planungstiefe"
        subtitle="Wie viele Schritte darf TRION vorausdenken, bevor er loslegt?"
        onBack={onBack}
      />
      <div className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        <div className="flex flex-wrap gap-2">
          {OPTIONS.map((o) => (
            <button
              key={o.id}
              type="button"
              onClick={() => onChange(o.id)}
              className={cn(
                'rounded-lg border px-4 py-2 text-[12px] font-medium transition',
                value === o.id
                  ? 'border-white/25 bg-white/8 text-white/95'
                  : 'border-white/10 text-white/50 hover:border-white/20 hover:text-white/80',
              )}
            >
              {o.label}
            </button>
          ))}
        </div>
        {current && (
          <p className="mt-4 text-[11px] text-white/35">{current.hint}</p>
        )}
      </div>
    </div>
  )
}
