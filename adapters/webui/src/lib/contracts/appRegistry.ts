import type { WindowDisplayMode } from '@/state/windowStore'

export type OpenWindowArgs = {
  appId: string
  title: string
  displayMode?: WindowDisplayMode
  size?: { width: number; height: number }
  position?: { x: number; y: number }
}

export interface AppDefinition {
  id: string
  label: string
  iconName?: string
  iconUrl?: string
  color: string      // Tailwind text-color class
  openArgs: OpenWindowArgs
  canPin: boolean
}

export const APP_REGISTRY: AppDefinition[] = [
  {
    id: 'launchpad',
    label: 'Launchpad',
    iconName: 'launchpad',
    color: 'text-white/70',
    canPin: false,
    openArgs: {
      appId: 'launchpad',
      title: 'Launchpad',
      size: { width: 700, height: 500 },
    },
  },
  {
    id: 'chat',
    label: 'Chat',
    iconName: 'chat',
    color: 'text-blue-400',
    canPin: true,
    openArgs: {
      appId: 'chat',
      title: 'TRION Chat',
      displayMode: 'panel',
      size: { width: 420, height: 600 },
    },
  },
  {
    id: 'settings',
    label: 'Einstellungen',
    iconName: 'settings',
    color: 'text-white/70',
    canPin: true,
    openArgs: {
      appId: 'settings',
      title: 'Einstellungen',
      size: { width: 800, height: 560 },
    },
  },
  {
    id: 'mcp',
    label: 'MCP Installer',
    iconName: 'mcp',
    color: 'text-white/70',
    canPin: true,
    openArgs: {
      appId: 'mcp',
      title: 'MCP Installer',
      size: { width: 880, height: 600 },
    },
  },
  {
    id: 'plugins',
    label: 'Plugins',
    iconName: 'plugins',
    color: 'text-white/70',
    canPin: true,
    openArgs: {
      appId: 'plugins',
      title: 'Plugins',
      size: { width: 980, height: 720 },
    },
  },
  {
    id: 'memory',
    label: 'Memory',
    iconName: 'memory',
    color: 'text-white/70',
    canPin: true,
    openArgs: {
      appId: 'memory',
      title: 'Memory',
      size: { width: 920, height: 640 },
    },
  },
]

export function getApp(id: string): AppDefinition | undefined {
  return APP_REGISTRY.find(a => a.id === id)
}
