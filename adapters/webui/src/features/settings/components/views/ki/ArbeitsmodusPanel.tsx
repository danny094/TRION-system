import { cn } from '@/lib/utils'
import { DetailHeader } from './DetailHeader'

export type AutonomyMode = 'manuell' | 'halbautomatisch' | 'autonom'

interface ArbeitsmodusProps {
  value: AutonomyMode
  onChange: (v: AutonomyMode) => void
  onBack: () => void
}

const MODES: {
  id: AutonomyMode
  icon: string
  label: string
  desc: string
  detail: string
  tint: string
  iconColor: string
}[] = [
  {
    id: 'manuell',
    icon: '🔒',
    label: 'Manuell',
    desc: 'Tool-Schritte halten grundsätzlich vor der Ausführung an',
    detail: 'Geeignet wenn du jeden Eingriff erst freigeben möchtest.',
    tint: 'bg-white/[0.04] border-white/20',
    iconColor: 'bg-white/10',
  },
  {
    id: 'halbautomatisch',
    icon: '⚡',
    label: 'Halbautomatisch',
    desc: 'Normale Schritte laufen durch, riskante Schritte fragen nach',
    detail: 'Das ist der Standardmodus für ausgewogene Autonomie.',
    tint: 'bg-purple-500/[0.07] border-purple-500/50',
    iconColor: 'bg-purple-500/20',
  },
  {
    id: 'autonom',
    icon: '🤖',
    label: 'Autonom',
    desc: 'Erlaubte Schritte laufen freier, Policy-Grenzen bleiben aktiv',
    detail: 'Approval-pflichtige Tools und harte Grenzen stoppen weiterhin.',
    tint: 'bg-amber-500/[0.07] border-amber-600/50',
    iconColor: 'bg-amber-500/15',
  },
]

export function ArbeitsmodusPanel({ value, onChange, onBack }: ArbeitsmodusProps) {
  return (
    <div className="flex flex-col gap-5">
      <DetailHeader
        title="Arbeitsmodus"
        subtitle="Der Arbeitsmodus steuert, wann TRION vor Tool-Schritten anhält und wann er innerhalb der erlaubten Grenzen weiterlaufen darf."
        onBack={onBack}
      />
      <div className="grid grid-cols-3 gap-3">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => onChange(m.id)}
            className={cn(
              'flex flex-col rounded-2xl border p-4 text-left transition',
              value === m.id ? m.tint : 'border-white/8 bg-white/[0.015] hover:bg-white/[0.03]',
            )}
          >
            <div className={cn('mb-3 flex h-7 w-7 items-center justify-center rounded-lg text-[16px]', m.iconColor)}>
              {m.icon}
            </div>
            <div className="text-[13px] font-medium text-white/90">{m.label}</div>
            <div className="mt-1.5 text-[11px] leading-relaxed text-white/45">{m.desc}</div>
            <div className="mt-3 text-[10px] leading-relaxed text-white/32">{m.detail}</div>
          </button>
        ))}
      </div>
      <div className="rounded-2xl border border-white/6 bg-white/[0.02] px-4 py-3 text-[11px] leading-relaxed text-white/48">
        <span className="text-white/72">Wichtig:</span> Der Arbeitsmodus lockert keine Safety-, Verifier- oder Tool-Policy-Grenzen.
        Er bestimmt nur, wie früh TRION innerhalb dieser Grenzen in <span className="text-white/72">WAITING</span> geht.
      </div>
    </div>
  )
}
