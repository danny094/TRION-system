import { create } from 'zustand'
import type { PluginSummary } from '@/lib/contracts/plugin'
import { deletePlugin, fetchPlugins, installPlugin, setPluginEnabled } from '@/features/plugins/api'

interface PluginState {
  items: PluginSummary[]
  loading: boolean
  refresh: () => Promise<void>
  upload: (file: File) => Promise<void>
  toggle: (pluginId: string, enabled: boolean) => Promise<void>
  remove: (pluginId: string) => Promise<void>
}

export const usePluginStore = create<PluginState>((set, get) => ({
  items: [],
  loading: false,
  refresh: async () => {
    set({ loading: true })
    try {
      const payload = await fetchPlugins()
      set({ items: payload.plugins, loading: false })
    } catch {
      set({ loading: false })
    }
  },
  upload: async (file) => {
    await installPlugin(file)
    await get().refresh()
  },
  toggle: async (pluginId, enabled) => {
    await setPluginEnabled(pluginId, enabled)
    await get().refresh()
  },
  remove: async (pluginId) => {
    await deletePlugin(pluginId)
    await get().refresh()
  },
}))
