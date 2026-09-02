import React from 'react'
import type { PluginSummary } from '@/lib/contracts/plugin'
import { fetchApiResponse } from '@/lib/api/client'

export interface PluginBridge {
  request: (path: string, options?: PluginRequestOptions) => Promise<PluginBridgeResponse>
  callTool: (name: string, args?: Record<string, unknown>) => Promise<PluginBridgeResponse>
}

export interface PluginRequestOptions {
  method?: string
  params?: Record<string, unknown>
  headers?: Record<string, string>
  json?: unknown
  body?: string
}

export interface PluginBridgeResponse {
  ok: boolean
  status: number
  data: unknown
}

export interface PluginHostProps {
  plugin: PluginSummary
  bridge: PluginBridge
  assetUrl: (assetPath: string) => string
}

export type PluginHostComponent = React.ComponentType<PluginHostProps>

export function pluginAssetUrl(plugin: PluginSummary, assetPath: string): string {
  return `/api/plugins/${encodeURIComponent(plugin.id)}/asset/${assetPath}`
}

export function pluginEntryMode(plugin: PluginSummary): 'iframe' | 'blocked' {
  const entry = plugin.entry.toLowerCase()
  return entry.endsWith('.html') ? 'iframe' : 'blocked'
}

export function createPluginBridge(plugin: PluginSummary): PluginBridge {
  return {
    request: (path, options) =>
      postBridge(plugin, '/bridge/request', {
        path,
        method: options?.method,
        params: options?.params,
        headers: options?.headers,
        json: options?.json,
        body: options?.body,
      }),
    callTool: (name, args) =>
      postBridge(plugin, `/bridge/tools/${encodeURIComponent(name)}`, { args: args || {} }),
  }
}

async function postBridge(plugin: PluginSummary, path: string, payload: unknown): Promise<PluginBridgeResponse> {
  const response = await fetchApiResponse(`/plugins/${encodeURIComponent(plugin.id)}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  })
  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json') ? await response.json() : await response.text()
  return { ok: true, status: response.status, data }
}
