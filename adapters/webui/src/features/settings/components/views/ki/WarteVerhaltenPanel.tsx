import { cn } from '@/lib/utils'
import { DetailHeader } from './DetailHeader'
import { useTranslation } from '@/lib/i18n'

export type WaitBehavior = 'sofort' | '30sek' | '2min' | 'immer'

interface Props { value: WaitBehavior; onChange: (v: WaitBehavior) => void; onBack: () => void }

export function WarteVerhaltenPanel({ value, onChange, onBack }: Props) {
  const { t } = useTranslation()
  const options = [
    { id: 'sofort' as const, label: t('autonomy.stopNow'), hint: t('autonomy.stopNowHint') },
    { id: '30sek' as const, label: t('autonomy.seconds30'), hint: t('autonomy.seconds30Hint') },
    { id: '2min' as const, label: t('autonomy.minutes2'), hint: t('autonomy.minutes2Hint') },
    { id: 'immer' as const, label: t('autonomy.always'), hint: t('autonomy.alwaysHint') },
  ]
  const current = options.find((o) => o.id === value)
  return (
    <div className="flex flex-col gap-5">
      <DetailHeader
        title={t('autonomy.waitTitle')}
        subtitle={t('autonomy.waitSubtitle')}
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
