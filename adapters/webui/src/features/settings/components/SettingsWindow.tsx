import { useEffect, useMemo, useState } from 'react'
import { Sliders, Cpu, Palette, Box, Key } from 'lucide-react'
import { cn } from '@/lib/utils'
import { AppIcon } from '@/components/icons/AppIcon'
import { GeneralPanel } from '@/features/settings/components/GeneralPanel'
import { AppearancePanel } from '@/features/settings/components/AppearancePanel'
import { ProviderSettingsPanel } from '@/features/settings/components/ProviderSettingsPanel'
import { ApiKeysPanel } from '@/features/settings/components/ApiKeysPanel'
import { KiVerhaltenPanel } from '@/features/settings/components/KiVerhaltenPanel'
import { PluginSettingsPanel } from '@/features/settings/components/PluginSettingsPanel'
import { usePluginStore } from '@/features/plugins/state/pluginStore'
import { settingsTabsFromPlugins, type PluginSettingsTab } from '@/lib/contracts/pluginPanels'

type BuiltinSettingsTab = 'allgemein' | 'ki-verhalten' | 'erscheinungsbild' | 'modelle' | 'api'
type SettingsTab = BuiltinSettingsTab | `plugin-settings:${string}`

interface TabConfig {
  id: BuiltinSettingsTab
  label: string
  icon: React.ReactNode
  tint: string
}

const TABS: TabConfig[] = [
  { id: 'allgemein',        label: 'Allgemein',        icon: <Sliders className="h-3 w-3" />, tint: '#6E6E73' },
  { id: 'ki-verhalten',     label: 'KI & Verhalten',   icon: <Cpu     className="h-3 w-3" />, tint: '#7F77DD' },
  { id: 'erscheinungsbild', label: 'Erscheinungsbild', icon: <Palette className="h-3 w-3" />, tint: '#D4537E' },
  { id: 'modelle',          label: 'Modelle',          icon: <Box     className="h-3 w-3" />, tint: '#378ADD' },
  { id: 'api',              label: 'API',              icon: <Key     className="h-3 w-3" />, tint: '#BA7517' },
]

export function SettingsWindow() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('allgemein')
  const plugins = usePluginStore((s) => s.items)
  const refreshPlugins = usePluginStore((s) => s.refresh)
  const pluginTabs = useMemo(() => settingsTabsFromPlugins(plugins), [plugins])
  const activePlugin = pluginTabs.find((item) => item.id === activeTab)
    ? plugins.find((item) => item.id === pluginTabs.find((tab) => tab.id === activeTab)?.pluginId)
    : undefined

  useEffect(() => {
    if (plugins.length === 0) {
      void refreshPlugins()
    }
  }, [plugins.length, refreshPlugins])

  useEffect(() => {
    if (activePlugin || !String(activeTab).startsWith('plugin-settings:')) {
      return
    }
    setActiveTab('allgemein')
  }, [activePlugin, activeTab])

  return (
    <div className="flex h-full text-sm">
      <Sidebar active={activeTab} onSelect={setActiveTab} pluginTabs={pluginTabs} />
      <main className="flex-1 overflow-y-auto px-8 py-7">
        {activeTab === 'allgemein'        && <GeneralPanel />}
        {activeTab === 'erscheinungsbild' && <AppearancePanel />}
        {activeTab === 'modelle'          && <ProviderSettingsPanel />}
        {activeTab === 'api'              && <ApiKeysPanel />}
        {activeTab === 'ki-verhalten'     && <KiVerhaltenPanel />}
        {activePlugin                      && <PluginSettingsPanel plugin={activePlugin} />}
      </main>
    </div>
  )
}

interface SidebarProps {
  active: SettingsTab
  onSelect: (tab: SettingsTab) => void
  pluginTabs: PluginSettingsTab[]
}

function Sidebar({ active, onSelect, pluginTabs }: SidebarProps) {
  return (
    <aside className="flex w-44 shrink-0 flex-col border-r border-white/8 bg-white/[0.015] px-3 py-4">
      <div className="mb-5 flex items-center gap-2.5 px-1">
        <div className="h-9 w-9 shrink-0 overflow-hidden rounded-xl bg-white/85">
          <AppIcon name="settings" className="h-full w-full" />
        </div>
        <div className="min-w-0">
          <div className="text-[13px] font-semibold leading-tight text-white/95">
            Einstellungen
          </div>
          <div className="mt-0.5 text-[10px] leading-tight text-white/35">
            v 1.0 · TRION
          </div>
        </div>
      </div>

      <nav className="flex flex-col gap-0.5">
        {TABS.map((tab) => (
          <TabButton
            key={tab.id}
            label={tab.label}
            icon={<span
              className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-white"
              style={{ backgroundColor: tab.tint }}
            >
              {tab.icon}
            </span>}
            active={tab.id === active}
            onClick={() => onSelect(tab.id)}
          />
        ))}
        {pluginTabs.length > 0 && (
          <div className="mt-3 border-t border-white/8 pt-3">
            <div className="px-2 pb-2 text-[10px] uppercase tracking-[0.18em] text-white/25">
              Plugins
            </div>
            <div className="flex flex-col gap-0.5">
              {pluginTabs.map((tab) => (
                <TabButton
                  key={tab.id}
                  label={tab.label}
                  icon={<div className="h-5 w-5 shrink-0 overflow-hidden rounded-md bg-white/10"><AppIcon src={tab.iconUrl} className="h-full w-full" /></div>}
                  active={tab.id === active}
                  onClick={() => onSelect(tab.id)}
                />
              ))}
            </div>
          </div>
        )}
      </nav>
    </aside>
  )
}

interface TabButtonProps {
  label: string
  icon: React.ReactNode
  active: boolean
  onClick: () => void
}

function TabButton({ label, icon, active, onClick }: TabButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-[12px] transition-colors duration-150',
        active
          ? 'bg-white/8 text-white/95'
          : 'text-white/55 hover:bg-white/[0.04] hover:text-white/85',
      )}
    >
      {icon}
      <span className="truncate">{label}</span>
    </button>
  )
}
