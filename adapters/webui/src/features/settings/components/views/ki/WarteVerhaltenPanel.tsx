import { cn } from '@/lib/utils'
import { DetailHeader } from './DetailHeader'

export type WaitBehavior = 'sofort' | '30sek' | '2min' | 'immer'

interface Props { value: WaitBehavior; onChange: (v: WaitBehavior) => void; onBack: () => void }

const OPTIONS: { id: WaitBehavior; label: string; hint: string }[] = [
  { id: 'sofort', label: 'Sofort stopp',  hint: 'Planung stoppt sofort wenn du zu tippen anfängst' },
  { id: '30sek',  label: '30 Sek',        hint: 'Gedanken laufen noch 30 Sekunden weiter' },
  { id: '2min',   label: '2 Min',         hint: 'Hintergrundplanung für bis zu 2 Minuten' },
  { id: 'immer',  label: 'Immer',         hint: 'TRION denkt ständig weiter — auch im Leerlauf' },
]

export function WarteVerhaltenPanel({ value, onChange, onBack }: Props) {
  const current = OPTIONS.find((o) => o.id === value)
  return (
    <div className="flex flex-col gap-5">
      <DetailHeader
        title="Warteverhalten"
        subtitle="Wie lange darf TRION im Hintergrund weiterplanen, während er auf deine Antwort wartet?"
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
