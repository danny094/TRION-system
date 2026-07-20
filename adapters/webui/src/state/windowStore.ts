import { create } from 'zustand'

export type WindowDisplayMode = 'floating' | 'panel' | 'fullscreen'

export interface WindowState {
  windowId: string
  appId: string
  title: string
  position?: { x: number; y: number }
  size?: { width: number; height: number }
  zIndex: number
  minimized: boolean
  maximized: boolean
  focused: boolean
  displayMode: WindowDisplayMode
}

interface WindowManagerStore {
  windows: WindowState[]
  openWindow: (window: Omit<WindowState, 'windowId' | 'zIndex' | 'minimized' | 'maximized' | 'focused' | 'displayMode'> & { displayMode?: WindowDisplayMode }) => void
  closeWindow: (windowId: string) => void
  focusWindow: (windowId: string) => void
  setDisplayMode: (windowId: string, mode: WindowDisplayMode) => void
  updateWindow: (windowId: string, updates: Partial<WindowState>) => void
}

let nextZIndex = 100

export const useWindowStore = create<WindowManagerStore>((set) => ({
  windows: [],
  openWindow: (win) => set((state) => {
    // Singleton-Apps: bereits offen? -> fokussieren statt neu öffnen
    const singletons = ['chat', 'launchpad', 'settings']
    if (singletons.includes(win.appId)) {
      const existing = state.windows.find(w => w.appId === win.appId)
      if (existing) {
        nextZIndex += 1
        return {
          windows: state.windows.map(w => ({
            ...w,
            focused: w.windowId === existing.windowId,
            minimized: w.windowId === existing.windowId ? false : w.minimized,
            zIndex: w.windowId === existing.windowId ? nextZIndex : w.zIndex
          }))
        }
      }
    }

    const windowId = `win_${Date.now()}`
    nextZIndex += 1
    const newWindow: WindowState = {
      ...win,
      windowId,
      zIndex: nextZIndex,
      minimized: false,
      maximized: false,
      focused: true,
      displayMode: win.displayMode ?? 'floating',
    }
    return { windows: [...state.windows.map(w => ({ ...w, focused: false })), newWindow] }
  }),
  closeWindow: (id) => set((state) => ({
    windows: state.windows.filter(w => w.windowId !== id)
  })),
  focusWindow: (id) => set((state) => {
    nextZIndex += 1
    return {
      windows: state.windows.map(w => ({
        ...w,
        focused: w.windowId === id,
        zIndex: w.windowId === id ? nextZIndex : w.zIndex
      }))
    }
  }),
  setDisplayMode: (id, mode) => set((state) => ({
    windows: state.windows.map(w => w.windowId === id ? { ...w, displayMode: mode } : w)
  })),
  updateWindow: (id, updates) => set((state) => ({
    windows: state.windows.map(w => w.windowId === id ? { ...w, ...updates } : w)
  }))
}))
