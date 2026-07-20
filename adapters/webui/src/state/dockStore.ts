import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { OpenWindowArgs } from '@/lib/contracts/appRegistry'

export interface DockApp {
  id: string
  label: string
  iconName?: string
  iconUrl?: string
  color: string
  openArgs: OpenWindowArgs
}

interface DockState {
  apps: DockApp[]
  addApp: (app: DockApp) => void
  removeApp: (id: string) => void
  reorderApps: (apps: DockApp[]) => void
  hasApp: (id: string) => boolean
}

export const useDockStore = create<DockState>()(
  persist(
    (set, get) => ({
      apps: [],
      addApp: (app) =>
        set((state) => {
          if (state.apps.some((a) => a.id === app.id)) return state
          return { apps: [...state.apps, app] }
        }),
      removeApp: (id) =>
        set((state) => ({ apps: state.apps.filter((a) => a.id !== id) })),
      reorderApps: (apps) => set({ apps }),
      hasApp: (id) => get().apps.some((a) => a.id === id),
    }),
    { name: 'trion-dock' }
  )
)
