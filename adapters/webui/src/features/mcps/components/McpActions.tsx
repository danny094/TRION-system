import { Power, Trash2 } from 'lucide-react'
import type { McpDetails } from '@/lib/contracts/mcp'
import { useTranslation } from '@/lib/i18n'

interface McpActionsProps {
  detail: McpDetails
  saving: boolean
  onToggle: () => void
  onRemove: () => void
}

export function McpActions({ detail, saving, onToggle, onRemove }: McpActionsProps) {
  const isActive = detail.mcp.enabled && detail.mcp.online
  const canManage = detail.editableConfig
  const { t } = useTranslation()

  return (
    <div className="flex items-center justify-between gap-2">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onToggle}
          disabled={!canManage || saving}
          className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-white/75 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Power className="h-3.5 w-3.5" />
          {isActive ? t('mcp.deactivate') : t('mcp.activate')}
        </button>
      </div>

      <button
        type="button"
        onClick={onRemove}
        disabled={!canManage || saving}
        className="inline-flex items-center gap-2 rounded-xl border border-rose-500/15 bg-rose-500/[0.06] px-3 py-2 text-xs text-rose-300 transition hover:border-rose-500/30 hover:bg-rose-500/15 disabled:cursor-not-allowed disabled:opacity-40"
        title={canManage ? t('mcp.uninstall') : t('mcp.coreReadOnly')}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}
