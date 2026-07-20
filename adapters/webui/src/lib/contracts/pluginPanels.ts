import type { PluginSummary } from '@/lib/contracts/plugin'

export type PluginSettingsTabId = `plugin-settings:${string}`

export interface PluginSettingsTab {
  id: PluginSettingsTabId
  label: string
  pluginId: string
  iconUrl?: string
}

export function settingsTabsFromPlugins(items: PluginSummary[]): PluginSettingsTab[] {
  return items
    .filter((item) => item.enabled && (item.kind === 'app' || item.kind === 'panel') && item.mount === 'settings.tab')
    .map((item) => ({
      id: `plugin-settings:${item.id}`,
      label: item.name,
      pluginId: item.id,
      iconUrl: item.icon ? `/api/plugins/${encodeURIComponent(item.id)}/asset/${item.icon}` : undefined,
    }))
}
