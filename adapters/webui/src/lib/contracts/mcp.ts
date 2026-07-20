export type McpTransport = 'http' | 'sse' | 'stdio'

export type McpStatus = 'active' | 'inactive' | 'error'

export interface McpSummary {
  name: string
  displayName: string
  version: string
  enabled: boolean
  online: boolean
  transport: McpTransport
  url: string
  description: string
  toolsCount: number
  iconUrl: string | null
  hasSettings: boolean
  launchpadEnabled: boolean
  launchpadLabel: string
  settingsMode: 'config' | 'host_panel' | 'plugin' | ''
}

export interface McpToolDefinition {
  name: string
  description: string
  inputSchema: Record<string, unknown>
}

export interface McpDetails {
  mcp: McpSummary
  tools: McpToolDefinition[]
  editableConfig: boolean
  rawConfig: string
}

export interface McpInstallResult {
  success: boolean
  mcp: {
    name: string
    display_name?: string
    version?: string
    description: string
    url: string
  }
  health?: {
    status?: string
    reason?: string
    reload_method?: string
  }
}
