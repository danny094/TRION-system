import { cn } from '@/lib/utils'
import type { PolicyBadge } from '../contracts'

const BADGE_LABELS: Record<PolicyBadge, string> = {
  global_enabled: 'Global',
  conversation_only: 'Nur hier',
  temporary: 'Temporaer',
  do_not_remember: 'Nicht merken',
  disabled: 'Aus',
}

const BADGE_TONE: Record<PolicyBadge, string> = {
  global_enabled: 'border-emerald-400/25 bg-emerald-500/10 text-emerald-100/85',
  conversation_only: 'border-sky-400/25 bg-sky-500/10 text-sky-100/85',
  temporary: 'border-amber-400/25 bg-amber-500/10 text-amber-100/85',
  do_not_remember: 'border-rose-400/25 bg-rose-500/10 text-rose-100/85',
  disabled: 'border-white/15 bg-white/5 text-white/60',
}

export function PrivacyBadge({ badge }: { badge: PolicyBadge }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.16em]',
        BADGE_TONE[badge],
      )}
    >
      {BADGE_LABELS[badge]}
    </span>
  )
}
