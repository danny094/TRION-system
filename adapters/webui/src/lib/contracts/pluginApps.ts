import type { AppDefinition } from '@/lib/contracts/appRegistry'
import type { PluginSummary } from '@/lib/contracts/plugin'

export const PLUGIN_APP_PREFIX = 'plugin:'

export function pluginAppId(pluginId: string): string {
  return `${PLUGIN_APP_PREFIX}${pluginId}`
}

export function isPluginAppId(appId: string): boolean {
  return appId.startsWith(PLUGIN_APP_PREFIX)
}

export function pluginIdFromAppId(appId: string): string {
  return appId.slice(PLUGIN_APP_PREFIX.length)
}

export function launchpadAppsFromPlugins(items: PluginSummary[]): AppDefinition[] {
  return items
    .filter((item) => item.enabled && item.kind === 'app' && item.mount === 'launchpad')
    .map((item) => ({
      id: pluginAppId(item.id),
      label: item.name,
      iconUrl: item.icon ? `/api/plugins/${encodeURIComponent(item.id)}/asset/${item.icon}` : undefined,
      color: 'text-white/70',
      canPin: true,
      openArgs: {
        appId: pluginAppId(item.id),
        title: item.name,
        size: { width: 980, height: 700 },
      },
    }))
}

export function findPluginApp(items: PluginSummary[], appId: string): AppDefinition | undefined {
  return launchpadAppsFromPlugins(items).find((app) => app.id === appId)
}
