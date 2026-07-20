import { Info, LayoutGrid, Download, Trash2, Folder, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import { AppIcon } from '@/components/icons/AppIcon'
import type { InstallerView } from '../state/mcpsStore'

interface McpsSidebarProps {
  view: InstallerView
  onSelectView: (view: InstallerView) => void
  activeCount: number
}

interface TabConfig {
  id: InstallerView
  label: string
  icon: React.ReactNode
}

const TABS: TabConfig[] = [
  { id: 'about',     label: 'About',     icon: <Info       className="h-4 w-4" /> },
  { id: 'all',       label: 'All',       icon: <LayoutGrid className="h-4 w-4" /> },
  { id: 'install',   label: 'Install',   icon: <Download   className="h-4 w-4" /> },
  { id: 'uninstall', label: 'Uninstall', icon: <Trash2     className="h-4 w-4" /> },
  { id: 'files',     label: 'Files',     icon: <Folder     className="h-4 w-4" /> },
  { id: 'news',      label: 'News',      icon: <Sparkles   className="h-4 w-4" /> },
]

export function McpsSidebar({ view, onSelectView, activeCount }: McpsSidebarProps) {
  return (
    <aside className="flex w-44 shrink-0 flex-col border-r border-white/8 bg-white/[0.015] px-3 py-4">
      {/* Header: Icon-Card + Title */}
      <div className="mb-5 flex items-center gap-2.5 px-1">
        <div className="h-9 w-9 shrink-0 overflow-hidden rounded-xl bg-white/85">
          <AppIcon name="mcp" className="h-full w-full" />
        </div>
        <div className="min-w-0">
          <div className="text-[13px] font-semibold leading-tight text-white/95">
            MCP Installer
          </div>
          <div className="mt-0.5 text-[10px] leading-tight text-white/35">
            v 1.0 · TRION
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-0.5">
        {TABS.map((tab) => (
          <TabButton
            key={tab.id}
            tab={tab}
            active={tab.id === view}
            onClick={() => onSelectView(tab.id)}
          />
        ))}
      </nav>

      {/* Footer: Runtime status */}
      <div className="mt-auto px-2 pt-4">
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.7)]" />
          <span className="text-[11px] font-medium text-white/75 tabular-nums">
            {activeCount} active
          </span>
        </div>
        <div className="mt-0.5 text-[10px] text-white/30">connected to runtime</div>
      </div>
    </aside>
  )
}

interface TabButtonProps {
  tab: TabConfig
  active: boolean
  onClick: () => void
}

function TabButton({ tab, active, onClick }: TabButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'group flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-[13px] transition-colors duration-150',
        active
          ? 'bg-white/8 text-white/95'
          : 'text-white/55 hover:bg-white/[0.04] hover:text-white/85',
      )}
    >
      <span
        className={cn(
          'shrink-0 transition-colors',
          active ? 'text-white/90' : 'text-white/45 group-hover:text-white/70',
        )}
      >
        {tab.icon}
      </span>
      <span>{tab.label}</span>
    </button>
  )
}
