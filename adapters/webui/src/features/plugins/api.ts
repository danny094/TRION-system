import { fetchApi } from '@/lib/api/client'
import type { PluginSummary } from '@/lib/contracts/plugin'

export function fetchPlugins(): Promise<{ plugins: PluginSummary[] }> {
  return fetchApi<{ plugins: any[] }>('/plugins/installed').then((payload) => ({
    plugins: (payload.plugins || []).map((item) => ({
      id: String(item?.id ?? ''),
      name: String(item?.name ?? ''),
      version: String(item?.version ?? ''),
      author: String(item?.author ?? ''),
      description: String(item?.description ?? ''),
      kind: item?.kind,
      mount: String(item?.mount ?? ''),
      icon: String(item?.icon ?? ''),
      entry: String(item?.entry ?? ''),
      enabled: Boolean(item?.enabled),
      requiresMcp: Array.isArray(item?.requires_mcp) ? item.requires_mcp.map(String) : [],
      missingMcp: Array.isArray(item?.missing_mcp) ? item.missing_mcp.map(String) : [],
    })),
  }))
}

export function installPlugin(file: File): Promise<{ success: boolean }> {
  const form = new FormData()
  form.append('file', file)
  return fetchApi('/plugins/install', { method: 'POST', body: form })
}

export function setPluginEnabled(pluginId: string, enabled: boolean): Promise<{ success: boolean }> {
  return fetchApi(`/plugins/${encodeURIComponent(pluginId)}/${enabled ? 'enable' : 'disable'}`, { method: 'POST' })
}

export function deletePlugin(pluginId: string): Promise<{ success: boolean }> {
  return fetchApi(`/plugins/${encodeURIComponent(pluginId)}`, { method: 'DELETE' })
}
