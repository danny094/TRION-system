import { cn } from '@/lib/utils'
import type { PolicyBadge } from '../contracts'
import { useTranslation } from '@/lib/i18n'

const BADGE_TONE: Record<PolicyBadge, string> = {
  global_enabled: 'border-emerald-400/25 bg-emerald-500/10 text-emerald-100/85',
  conversation_only: 'border-sky-400/25 bg-sky-500/10 text-sky-100/85',
  temporary: 'border-amber-400/25 bg-amber-500/10 text-amber-100/85',
  do_not_remember: 'border-rose-400/25 bg-rose-500/10 text-rose-100/85',
  disabled: 'border-white/15 bg-white/5 text-white/60',
}

export function PrivacyBadge({ badge }: { badge: PolicyBadge }) {
  const { t } = useTranslation()
  const badgeLabels: Record<PolicyBadge, string> = {
    global_enabled: t('memory.global'),
    conversation_only: t('memory.hereOnly'),
    temporary: t('memory.temporary'),
    do_not_remember: t('memory.doNotRemember'),
    disabled: t('memory.off'),
  }
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.16em]',
        BADGE_TONE[badge],
      )}
    >
      {badgeLabels[badge]}
    </span>
  )
}
