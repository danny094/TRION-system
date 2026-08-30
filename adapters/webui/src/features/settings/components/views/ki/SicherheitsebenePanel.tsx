import { Lock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { DetailHeader } from './DetailHeader'
import { useTranslation } from '@/lib/i18n'

interface Props { askBeforeTools: boolean; onToggle: () => void; onBack: () => void }

export function SicherheitsebenePanel({ askBeforeTools, onToggle, onBack }: Props) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col gap-5">
      <DetailHeader
        title={t('autonomy.safetyTitle')}
        subtitle={t('autonomy.safetySubtitle')}
        onBack={onBack}
      />
      <div className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        <ToggleRow
          label={t('autonomy.skipThinking')}
          description={t('autonomy.skipThinkingHint')}
          checked={askBeforeTools}
          onToggle={onToggle}
        />
        <LockedRow
          label={t('autonomy.hardLimits')}
          description={t('autonomy.hardLimitsHint')}
        />
        <div className="mt-4 rounded-xl border border-white/6 bg-black/10 px-3 py-3 text-[11px] leading-relaxed text-white/38">
          <span className="text-white/68">{t('autonomy.important')}</span> {t('autonomy.safetyNote')}
        </div>
      </div>
    </div>
  )
}

function ToggleRow({ label, description, checked, onToggle }: {
  label: string; description: string; checked: boolean; onToggle: () => void
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/5 py-3">
      <div>
        <div className="text-[12px] text-white/85">{label}</div>
        <div className="mt-1 text-[11px] text-white/40">{description}</div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={onToggle}
        className={cn(
          'relative h-5 w-9 shrink-0 rounded-full transition-colors duration-200',
          checked ? 'bg-emerald-500/80' : 'bg-white/15',
        )}
      >
        <span className={cn(
          'absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200',
          checked ? 'translate-x-4' : 'translate-x-0.5',
        )} />
      </button>
    </div>
  )
}

function LockedRow({ label, description }: { label: string; description: string }) {
  const { t } = useTranslation()
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div>
        <div className="flex items-center gap-2">
          <span className="text-[12px] text-white/60">{label}</span>
          <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] px-1.5 py-0.5 text-[9px] text-white/40">
            <Lock className="h-2.5 w-2.5" />
            {t('autonomy.alwaysOn')}
          </span>
        </div>
        <div className="mt-1 text-[11px] text-white/35">{description}</div>
      </div>
      <div className="relative h-5 w-9 shrink-0 rounded-full bg-emerald-500/60 opacity-50">
        <span className="absolute right-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow-sm" />
      </div>
    </div>
  )
}
