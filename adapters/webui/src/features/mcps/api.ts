import { fetchApi } from '@/lib/api/client'
import type {
  McpDetails,
  McpInstallResult,
  McpSummary,
  McpToolDefinition,
} from '@/lib/contracts/mcp'

interface ListResponseItem {
  name?: string
  display_name?: string
  version?: string
  enabled?: boolean
  online?: boolean
  transport?: string
  url?: string
  description?: string
  tools_count?: number
  ui?: { icon?: string }
  has_settings?: boolean
  launchpad_enabled?: boolean
  launchpad_label?: string
  settings_mode?: string
}

interface McpDetailsResponse {
  mcp?: ListResponseItem
  tools?: Array<{
    name?: string
    description?: string
    inputSchema?: Record<string, unknown>
  }>
}

interface McpConfigResponse {
  config?: Record<string, unknown>
}

export async function fetchInstalledMcps(): Promise<McpSummary[]> {
  const response = await fetchApi<{ mcps?: ListResponseItem[] }>('/mcp/list')
  return listFromResponse(response.mcps)
}

export async function fetchMcpDetails(name: string): Promise<McpDetails> {
  const details = await fetchApi<McpDetailsResponse>(`/mcp/${encodeURIComponent(name)}/details`)
  const rawConfig = await fetchRawConfig(name)
  return {
    mcp: summaryFromResponse(details.mcp),
    tools: toolsFromResponse(details.tools),
    editableConfig: rawConfig.length > 0,
    rawConfig,
  }
}

export async function installMcp(file: File): Promise<McpInstallResult> {
  const formData = new FormData()
  formData.append('file', file)
  return fetchApi<McpInstallResult>('/mcp/install', {
    method: 'POST',
    body: formData,
  })
}

export async function uninstallMcp(name: string): Promise<{ success: boolean }> {
  return fetchApi<{ success: boolean }>(`/mcp/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  })
}

export async function toggleMcp(name: string): Promise<{ success: boolean; enabled: boolean }> {
  return fetchApi<{ success: boolean; enabled: boolean }>(`/mcp/${encodeURIComponent(name)}/toggle`, {
    method: 'POST',
  })
}

async function fetchRawConfig(name: string): Promise<string> {
  try {
    const response = await fetchApi<McpConfigResponse>(`/mcp/${encodeURIComponent(name)}/config`)
    return JSON.stringify(response.config ?? {}, null, 2)
  } catch {
    return ''
  }
}

function listFromResponse(items: ListResponseItem[] | undefined): McpSummary[] {
  return (items ?? []).map(summaryFromResponse)
}

function summaryFromResponse(item: ListResponseItem | undefined): McpSummary {
  const name = String(item?.name ?? '')
  return {
    name,
    displayName: String(item?.display_name ?? name),
    version: String(item?.version ?? ''),
    enabled: Boolean(item?.enabled),
    online: Boolean(item?.online),
    transport: transportFromValue(item?.transport),
    url: String(item?.url ?? ''),
    description: String(item?.description ?? ''),
    toolsCount: Number(item?.tools_count ?? 0),
    iconUrl: item?.ui?.icon ? `/api/mcp/${encodeURIComponent(name)}/icon` : null,
    hasSettings: Boolean(item?.has_settings),
    launchpadEnabled: Boolean(item?.launchpad_enabled),
    launchpadLabel: String(item?.launchpad_label ?? ''),
    settingsMode: settingsModeFromValue(item?.settings_mode),
  }
}

function toolsFromResponse(items: McpDetailsResponse['tools']): McpToolDefinition[] {
  return (items ?? []).map((item) => ({
    name: String(item?.name ?? ''),
    description: String(item?.description ?? ''),
    inputSchema: item?.inputSchema ?? {},
  }))
}

function transportFromValue(value: unknown): McpSummary['transport'] {
  if (value === 'http' || value === 'sse' || value === 'stdio') {
    return value
  }
  return 'http'
}

function settingsModeFromValue(value: unknown): McpSummary['settingsMode'] {
  if (value === 'config' || value === 'host_panel' || value === 'plugin') {
    return value
  }
  return ''
}

export async function updateMcpConfig(
  name: string,
  config: Record<string, unknown>,
): Promise<{ success: boolean; name: string; config: Record<string, unknown> }> {
  return fetchApi<{ success: boolean; name: string; config: Record<string, unknown> }>(
    `/mcp/${encodeURIComponent(name)}/config`,
    {
      method: 'PUT',
      body: JSON.stringify({ config }),
    },
  )
}
