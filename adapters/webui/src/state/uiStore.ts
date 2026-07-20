import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type FontSize = 'sm' | 'md' | 'lg' | 'xl'
export type AppearanceMode = 'auto' | 'light' | 'dark'
export type BackgroundSource = 'own' | 'system'

export const FONT_SIZE_PX: Record<FontSize, number> = {
  sm: 13,
  md: 16,
  lg: 18,
  xl: 20,
}

export const FONT_SIZE_LABELS: Record<FontSize, string> = {
  sm: 'Klein',
  md: 'Mittel',
  lg: 'Groß',
  xl: 'Sehr groß',
}

interface UiState {
  fontSize: FontSize
  backgroundImage: string | null
  backgroundSource: BackgroundSource
  ownBackgrounds: string[]
  accentColor: string
  customThemeName: string
  appearanceMode: AppearanceMode
  dockAutoHide: boolean
  setFontSize: (size: FontSize) => void
  setBackgroundImage: (dataUrl: string | null) => void
  setBackgroundSource: (source: BackgroundSource) => void
  addOwnBackground: (dataUrl: string) => void
  removeOwnBackground: (index: number) => void
  setAccentColor: (hex: string) => void
  setCustomThemeName: (name: string) => void
  setAppearanceMode: (mode: AppearanceMode) => void
  setDockAutoHide: (enabled: boolean) => void
}

export const useUiStore = create<UiState>()(
  persist(
    (set, get) => ({
      fontSize: 'md',
      backgroundImage: null,
      backgroundSource: 'own',
      ownBackgrounds: [],
      accentColor: '#eab308',
      customThemeName: '',
      appearanceMode: 'auto',
      dockAutoHide: false,
      setFontSize: (size) => set({ fontSize: size }),
      setBackgroundImage: (dataUrl) => set({ backgroundImage: dataUrl }),
      setBackgroundSource: (source) => set({ backgroundSource: source }),
      addOwnBackground: (dataUrl) =>
        set({ ownBackgrounds: [...get().ownBackgrounds, dataUrl] }),
      removeOwnBackground: (index) =>
        set({ ownBackgrounds: get().ownBackgrounds.filter((_, i) => i !== index) }),
      setAccentColor: (hex) => set({ accentColor: hex }),
      setCustomThemeName: (name) => set({ customThemeName: name }),
      setAppearanceMode: (mode) => set({ appearanceMode: mode }),
      setDockAutoHide: (enabled) => set({ dockAutoHide: enabled }),
    }),
    { name: 'trion-ui' }
  )
)
