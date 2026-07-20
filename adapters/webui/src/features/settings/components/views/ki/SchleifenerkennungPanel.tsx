import { cn } from '@/lib/utils'
import { DetailHeader } from './DetailHeader'

export type LoopSensitivity = 2 | 3 | 5 | 10

interface Props {
  active: boolean
  sensitivity: LoopSensitivity
  onToggle: () => void
  onSensitivity: (v: LoopSensitivity) => void
  onBack: () => void
}

const SENSITIVITY_OPTIONS: { value: LoopSensitivity; label: string }[] = [
  { value: 2,  label: '2×' },
  { value: 3,  label: '3×' },
  { value: 5,  label: '5×' },
  { value: 10, label: '10×' },
]

export function SchleifenerkennungPanel({ active, sensitivity, onToggle, onSensitivity, onBack }: Props) {
  return (
    <div className="flex flex-col gap-5">
      <DetailHeader
        title="Schleifenerkennung"
        subtitle="TRION erkennt wenn er im Kreis läuft und unterbricht den Task automatisch."
        onBack={onBack}
      />
      <div className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        <div className="flex items-center justify-between gap-4 border-b border-white/5 pb-4">
          <div>
            <div className="text-[12px] text-white/85">Schleifenerkennung aktiv</div>
            <div className="mt-1 text-[11px] text-white/40">Erkennt identische Tool-Calls in Folge</div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={active}
            onClick={onToggle}
            className={cn(
              'relative h-5 w-9 shrink-0 rounded-full transition-colors duration-200',
              active ? 'bg-emerald-500/80' : 'bg-white/15',
            )}
          >
            <span className={cn(
              'absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200',
              active ? 'translate-x-4' : 'translate-x-0.5',
            )} />
          </button>
        </div>
        <div className={cn('pt-4 transition', !active && 'pointer-events-none opacity-35')}>
          <div className="mb-3 text-[11px] text-white/45">
            Empfindlichkeit — nach wie vielen Wiederholungen bricht TRION ab?
          </div>
          <div className="flex gap-2">
            {SENSITIVITY_OPTIONS.map((o) => (
              <button
                key={o.value}
                type="button"
                onClick={() => onSensitivity(o.value)}
                className={cn(
                  'rounded-lg border px-4 py-2 font-mono text-[12px] transition',
                  sensitivity === o.value
                    ? 'border-white/25 bg-white/8 text-white/95'
                    : 'border-white/10 text-white/50 hover:border-white/20 hover:text-white/80',
                )}
              >
                {o.label}
              </button>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-white/30">
            Unterbricht nach {sensitivity} identischen Wiederholungen
          </p>
        </div>
      </div>
    </div>
  )
}
