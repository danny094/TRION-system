import { AlertCircle, CheckCircle2, HardDrive, Power, Server, TerminalSquare, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { McpDetails, McpStatus } from '@/lib/contracts/mcp'
import { McpActions } from './McpActions'
import { McpManifestView } from './McpManifestView'
import { useTranslation } from '@/lib/i18n'

interface McpDetailProps {
  detail: McpDetails
  saving: boolean
  onToggle: () => void
  onRemove: () => void
  onClose: () => void
}

export function McpDetail({ detail, saving, onToggle, onRemove, onClose }: McpDetailProps) {
  const { t } = useTranslation()
  const status = statusForMcp(detail)
  const rawJson = detail.rawConfig || JSON.stringify(detail.mcp, null, 2)

  return (
    <aside className="flex h-full w-[420px] shrink-0 flex-col border-l border-white/8 bg-white/3">
      <header className="relative border-b border-white/8 p-5">
        <button
          type="button"
          onClick={onClose}
          aria-label={t('common.close')}
          className="absolute right-4 top-4 rounded-full p-1 text-white/40 transition-colors hover:bg-white/5 hover:text-white/80"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-white/80 shadow-[0_8px_32px_rgba(234,179,8,0.08)]">
            <Server className="h-7 w-7" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-base font-semibold text-white/95">{detail.mcp.name}</h2>
            <div className="mt-1 flex items-center gap-2">
              <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] uppercase text-white/55">
                {detail.mcp.transport}
              </span>
              <span className="text-xs text-white/40">{t('mcp.tools', { count: detail.mcp.toolsCount })}</span>
            </div>
          </div>
        </div>

        <StatusBadge status={status} toolsCount={detail.mcp.toolsCount} />
      </header>

      <div className="flex-1 space-y-6 overflow-y-auto p-5">
        <section>
          <p className="text-sm leading-relaxed text-white/70">{detail.mcp.description || t('mcp.noDescription')}</p>
        </section>

        <div className="grid grid-cols-2 gap-3">
          <ProvidesBox
            title={t('mcp.runtime')}
            rows={[
              { icon: <TerminalSquare className="h-3.5 w-3.5" />, value: t('mcp.tools', { count: detail.mcp.toolsCount }) },
              { icon: <Server className="h-3.5 w-3.5" />, value: detail.mcp.transport },
              { icon: <HardDrive className="h-3.5 w-3.5" />, value: detail.mcp.url || '—' },
            ]}
          />
          <ProvidesBox
            title={t('mcp.mode')}
            rows={[
              { icon: null, value: detail.editableConfig ? t('mcp.custom') : t('mcp.core') },
              { icon: null, value: detail.mcp.enabled ? t('common.enabled') : t('mcp.disabled') },
              { icon: null, value: detail.mcp.online ? t('common.online') : t('common.offline') },
            ]}
          />
        </div>

        <ToolsList tools={detail.tools} />
        <McpManifestView rawJson={rawJson} />
      </div>

      <div className="border-t border-white/8 bg-white/[0.02] p-4">
        <McpActions
          detail={detail}
          saving={saving}
          onToggle={onToggle}
          onRemove={onRemove}
        />
      </div>
    </aside>
  )
}

function StatusBadge({ status, toolsCount }: { status: McpStatus; toolsCount: number }) {
  const { t } = useTranslation()
  const styles = {
    active: { cls: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300', label: t('mcp.running'), Icon: CheckCircle2 },
    inactive: { cls: 'border-white/10 bg-white/5 text-white/55', label: t('mcp.disabled'), Icon: Power },
    error: { cls: 'border-rose-500/20 bg-rose-500/10 text-rose-300', label: t('mcp.error'), Icon: AlertCircle },
  } as const

  const { cls, label, Icon } = styles[status]

  return (
    <div className="mt-4 flex items-center gap-2 text-xs">
      <span className={cn('inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1', cls)}>
        <Icon className="h-3.5 w-3.5" />
        {label}
      </span>
      {toolsCount > 0 && (
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-white/55">
          {t('mcp.registeredTools', { count: toolsCount })}
        </span>
      )}
    </div>
  )
}

interface ProvidesBoxProps {
  title: string
  rows: Array<{ icon: React.ReactNode; value: string }>
  mono?: boolean
}

function ProvidesBox({ title, rows, mono }: ProvidesBoxProps) {
  return (
    <section className="rounded-2xl border border-white/8 bg-white/[0.03] p-3">
      <h3 className="mb-2 text-xs uppercase tracking-[0.14em] text-white/35">{title}</h3>
      <ul className={cn('space-y-1.5 text-xs text-white/65', mono && 'font-mono')}>
        {rows.length === 0 ? (
          <li className="text-white/30">—</li>
        ) : (
          rows.map((row, i) => (
            <li key={i} className="flex items-center gap-2">
              {row.icon && <span className="text-white/35">{row.icon}</span>}
              <span className="truncate">{row.value}</span>
            </li>
          ))
        )}
      </ul>
    </section>
  )
}

function ToolsList({ tools }: { tools: McpDetails['tools'] }) {
  const { t } = useTranslation()
  return (
    <section>
      <h3 className="mb-3 text-xs uppercase tracking-[0.14em] text-white/35">{t('mcp.registeredToolsTitle')}</h3>
      <div className="space-y-2">
        {tools.length === 0 ? (
          <div className="rounded-2xl border border-white/8 bg-black/20 px-4 py-3 text-xs text-white/35">
            {t('mcp.noTools')}
          </div>
        ) : (
          tools.map((tool) => (
            <div
              key={tool.name}
              className="rounded-2xl border border-white/8 bg-black/20 px-4 py-3"
            >
              <div className="font-mono text-xs text-white/80">{tool.name}</div>
              <div className="mt-1 text-xs text-white/45">{tool.description || t('mcp.noDescription')}</div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}

function statusForMcp(detail: McpDetails): McpStatus {
  if (!detail.mcp.enabled) return 'inactive'
  return detail.mcp.online ? 'active' : 'error'
}
