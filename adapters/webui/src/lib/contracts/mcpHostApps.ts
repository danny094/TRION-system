import type { AppDefinition } from '@/lib/contracts/appRegistry'
import type { McpSummary } from '@/lib/contracts/mcp'

export const MCP_SETTINGS_APP_PREFIX = 'mcp-settings:'

export function mcpSettingsAppId(name: string): string {
  return `${MCP_SETTINGS_APP_PREFIX}${name}`
}

export function isMcpSettingsAppId(appId: string): boolean {
  return appId.startsWith(MCP_SETTINGS_APP_PREFIX)
}

export function mcpNameFromSettingsAppId(appId: string): string {
  return appId.slice(MCP_SETTINGS_APP_PREFIX.length)
}

export function launchpadAppsFromMcps(items: McpSummary[]): AppDefinition[] {
  return items
    .filter((item) => item.launchpadEnabled)
    .map((item) => ({
      id: mcpSettingsAppId(item.name),
      label: item.launchpadLabel || item.displayName,
      iconUrl: item.iconUrl || undefined,
      color: 'text-white/70',
      canPin: true,
      openArgs: {
        appId: mcpSettingsAppId(item.name),
        title: `${item.displayName} Settings`,
        size: { width: 760, height: 560 },
      },
    }))
}

export function findMcpHostApp(items: McpSummary[], appId: string): AppDefinition | undefined {
  return launchpadAppsFromMcps(items).find((app) => app.id === appId)
}
