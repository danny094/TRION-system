import { motion } from 'framer-motion'
import { ChevronRight, Server } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { McpStatus, McpSummary } from '@/lib/contracts/mcp'
import { useTranslation } from '@/lib/i18n'

interface McpListItemProps {
  mcp: McpSummary
  active: boolean
  index: number
  onSelect: () => void
}

const STATUS_DOT: Record<McpStatus, string> = {
  active: 'bg-emerald-400',
  inactive: 'bg-white/30',
  error: 'bg-rose-400',
}

export function McpListItem({ mcp, active, index, onSelect }: McpListItemProps) {
  const status = statusForMcp(mcp)
  const { t } = useTranslation()
  const statusLabels: Record<McpStatus, string> = {
    active: t('mcp.statusRunning'),
    inactive: t('mcp.statusOff'),
    error: t('mcp.statusError'),
  }

  return (
    <motion.button
      type="button"
      onClick={onSelect}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.18 }}
      className={cn(
        'group flex w-full items-center gap-3 rounded-2xl border px-3 py-2.5 text-left transition-all',
        active
          ? 'border-primary/30 bg-primary/[0.08]'
          : 'border-white/8 bg-white/[0.02] hover:border-white/15 hover:bg-white/[0.04]',
      )}
    >
      <div className="relative shrink-0">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/8 bg-white/5 text-white/70">
          <Server className="h-5 w-5" />
        </div>
        <span
          className={cn(
            'absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-black/60',
            STATUS_DOT[status],
          )}
          title={statusLabels[status]}
        />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-white/85">
            {mcp.name}
          </span>
          <span className="shrink-0 rounded-full border border-white/10 bg-white/5 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-white/45">
            {mcp.transport}
          </span>
        </div>
        <div className="truncate text-xs text-white/40">
          {t('mcp.toolsWithStatus', { count: mcp.toolsCount, status: statusLabels[status] })}
        </div>
      </div>

      <ChevronRight
        className={cn(
          'h-4 w-4 shrink-0 transition-colors',
          active ? 'text-primary' : 'text-white/25 group-hover:text-white/45',
        )}
      />
    </motion.button>
  )
}

function statusForMcp(mcp: McpSummary): McpStatus {
  if (!mcp.enabled) return 'inactive'
  return mcp.online ? 'active' : 'error'
}
