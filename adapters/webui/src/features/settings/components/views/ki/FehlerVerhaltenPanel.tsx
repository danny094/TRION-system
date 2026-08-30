import { cn } from '@/lib/utils'
import { DetailHeader } from './DetailHeader'
import { useTranslation } from '@/lib/i18n'

export type ErrorBehavior = 'retry' | 'ask' | 'abort'

interface Props { value: ErrorBehavior; onChange: (v: ErrorBehavior) => void; onBack: () => void }

export function FehlerVerhaltenPanel({ value, onChange, onBack }: Props) {
  const { t } = useTranslation()
  const options = [
    { id: 'retry' as const, label: t('autonomy.retry'), desc: t('autonomy.retryHint') },
    { id: 'ask' as const, label: t('autonomy.ask'), desc: t('autonomy.askHint') },
    { id: 'abort' as const, label: t('autonomy.abort'), desc: t('autonomy.abortHint') },
  ]
  return (
    <div className="flex flex-col gap-5">
      <DetailHeader
        title={t('autonomy.errorTitle')}
        subtitle={t('autonomy.errorSubtitle')}
        onBack={onBack}
      />
      <div className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        {options.map((o, i) => (
          <button
            key={o.id}
            type="button"
            onClick={() => onChange(o.id)}
            className={cn(
              'flex w-full items-center gap-3 py-3 text-left transition',
              i < options.length - 1 && 'border-b border-white/5',
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
