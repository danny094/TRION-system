import { create } from 'zustand'
import type {
  McpDetails,
  McpInstallResult,
  McpSummary,
} from '@/lib/contracts/mcp'
import {
  fetchMcpDetails,
  fetchInstalledMcps,
  installMcp,
  toggleMcp,
  uninstallMcp,
} from '../api'

interface McpsState {
  installerView: InstallerView
  search: string
  selectedName: string | null
  modalOpen: boolean
  items: McpSummary[]
  details: Record<string, McpDetails>
  loading: boolean
  detailLoading: boolean
  saving: boolean
  error: string | null
  setInstallerView: (view: InstallerView) => void
  setSearch: (value: string) => void
  select: (name: string | null) => Promise<void>
  openModal: () => void
  closeModal: () => void
  refresh: () => Promise<void>
  uploadBundle: (file: File) => Promise<McpInstallResult>
  toggleSelected: () => Promise<void>
  removeSelected: () => Promise<void>
  toggleByName: (name: string) => Promise<void>
  removeByName: (name: string) => Promise<void>
}

export type InstallerView = 'about' | 'all' | 'install' | 'uninstall' | 'files' | 'news'

export const useMcpsStore = create<McpsState>((set, get) => ({
  installerView: 'about',
  search: '',
  selectedName: null,
  modalOpen: false,
  items: [],
  details: {},
  loading: false,
  detailLoading: false,
  saving: false,
  error: null,

  setInstallerView: (installerView) => set({ installerView }),
  setSearch: (search) => set({ search }),
  openModal: () => set({ modalOpen: true }),
  closeModal: () => set({ modalOpen: false }),
  select: async (selectedName) => {
    set({ selectedName })
    if (!selectedName || get().details[selectedName]) {
      return
    }
    set({ detailLoading: true, error: null })
    try {
      const detail = await fetchMcpDetails(selectedName)
      set((state) => ({
        details: { ...state.details, [selectedName]: detail },
        detailLoading: false,
      }))
    } catch (err) {
      set({
        detailLoading: false,
        error: err instanceof Error ? err.message : 'MCP-Details konnten nicht geladen werden.',
      })
    }
  },
  refresh: async () => {
    set({ loading: true, error: null })
    try {
      const items = await fetchInstalledMcps()
      const next: Partial<McpsState> = { items, loading: false }
      const { selectedName } = get()
      if (!selectedName && items.length > 0) {
        next.selectedName = items[0].name
      } else if (selectedName && !items.some((item) => item.name === selectedName)) {
        next.selectedName = items[0]?.name ?? null
      }
      set(next)
      if (next.selectedName) {
        await get().select(next.selectedName)
      }
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : 'MCPs konnten nicht geladen werden.',
      })
    }
  },
  uploadBundle: async (file) => {
    set({ saving: true, error: null })
    try {
      const result = await installMcp(file)
      await get().refresh()
      await get().select(result.mcp.name)
      set({ saving: false, modalOpen: false })
      return result
    } catch (err) {
      set({
        saving: false,
        error: err instanceof Error ? err.message : 'MCP-Bundle konnte nicht installiert werden.',
      })
      throw err
    }
  },
  toggleSelected: async () => {
    const { selectedName } = get()
    if (!selectedName) return
    set({ saving: true, error: null })
    try {
      await toggleMcp(selectedName)
      set((state) => {
        const detail = state.details[selectedName]
        if (!detail) return { saving: false }
        return {
          saving: false,
          details: {
            ...state.details,
            [selectedName]: {
              ...detail,
              mcp: { ...detail.mcp, enabled: !detail.mcp.enabled },
            },
          },
        }
      })
      await get().refresh()
    } catch (err) {
      set({
        saving: false,
        error: err instanceof Error ? err.message : 'MCP konnte nicht umgeschaltet werden.',
      })
    }
  },
  removeSelected: async () => {
    const { selectedName } = get()
    if (!selectedName) return
    set({ saving: true, error: null })
    try {
      await uninstallMcp(selectedName)
      set((state) => {
        const nextDetails = { ...state.details }
        delete nextDetails[selectedName]
        return { details: nextDetails, saving: false }
      })
      await get().refresh()
    } catch (err) {
      set({
        saving: false,
        error: err instanceof Error ? err.message : 'MCP konnte nicht entfernt werden.',
      })
    }
  },
  toggleByName: async (name) => {
    set({ saving: true, error: null })
    try {
      await toggleMcp(name)
      await get().refresh()
      set({ saving: false })
    } catch (err) {
      set({
        saving: false,
        error: err instanceof Error ? err.message : 'MCP konnte nicht umgeschaltet werden.',
      })
    }
  },
  removeByName: async (name) => {
    set({ saving: true, error: null })
    try {
      await uninstallMcp(name)
      set((state) => {
        const nextDetails = { ...state.details }
        delete nextDetails[name]
        return { details: nextDetails, saving: false }
      })
      await get().refresh()
    } catch (err) {
      set({
        saving: false,
        error: err instanceof Error ? err.message : 'MCP konnte nicht entfernt werden.',
      })
    }
  },
}))
