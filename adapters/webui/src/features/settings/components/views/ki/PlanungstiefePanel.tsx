import { cn } from '@/lib/utils'
import { DetailHeader } from './DetailHeader'
import { useTranslation } from '@/lib/i18n'

export type PlanningDepth = 'schnell' | 'normal' | 'gründlich' | 'unbegrenzt'

interface Props { value: PlanningDepth; onChange: (v: PlanningDepth) => void; onBack: () => void }

export function PlanungstiefePanel({ value, onChange, onBack }: Props) {
  const { t } = useTranslation()
  const options = [
    { id: 'schnell' as const, label: t('autonomy.fast'), hint: t('autonomy.fastHint') },
    { id: 'normal' as const, label: t('autonomy.normal'), hint: t('autonomy.normalHint') },
    { id: 'gründlich' as const, label: t('autonomy.thorough'), hint: t('autonomy.thoroughHint') },
    { id: 'unbegrenzt' as const, label: t('autonomy.unlimited'), hint: t('autonomy.unlimitedHint') },
  ]
  const current = options.find((o) => o.id === value)
  return (
    <div className="flex flex-col gap-5">
      <DetailHeader
        title={t('autonomy.planningTitle')}
        subtitle={t('autonomy.planningSubtitle')}
        onBack={onBack}
      />
      <div className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        <div className="flex flex-wrap gap-2">
          {options.map((o) => (
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
