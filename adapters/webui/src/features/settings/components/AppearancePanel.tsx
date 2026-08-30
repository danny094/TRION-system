import { useRef } from 'react'
import { Sun, Moon, SunMoon, Plus } from 'lucide-react'
import {
  useUiStore,
  FONT_SIZE_PX,
  type FontSize,
  type AppearanceMode,
} from '@/state/uiStore'
import { cn } from '@/lib/utils'
import { BackgroundSection, FontSizeCard, SectionLabel, SwatchButton } from './AppearancePanelParts'

const PRESETS = [
  { label: 'Gelb',  value: '#eab308' },
  { label: 'Blau',  value: '#3b82f6' },
  { label: 'Lila',  value: '#a855f7' },
  { label: 'Grün',  value: '#22c55e' },
  { label: 'Rot',   value: '#ef4444' },
  { label: 'Weiß',  value: '#e5e7eb' },
]

const FONT_SIZES: FontSize[] = ['lg', 'md', 'sm']

const MODES: { id: AppearanceMode; label: string; icon: React.ReactNode }[] = [
  { id: 'auto',  label: 'Automatisch', icon: <SunMoon className="h-3.5 w-3.5" /> },
  { id: 'light', label: 'Hell',        icon: <Sun     className="h-3.5 w-3.5" /> },
  { id: 'dark',  label: 'Dunkel',      icon: <Moon    className="h-3.5 w-3.5" /> },
]

export function AppearancePanel() {
  const {
    fontSize, setFontSize,
    accentColor, setAccentColor,
    customThemeName, setCustomThemeName,
    backgroundSource, setBackgroundSource,
    ownBackgrounds, addOwnBackground, removeOwnBackground,
    backgroundImage, setBackgroundImage,
    appearanceMode, setAppearanceMode,
  } = useUiStore()

  const colorInputRef = useRef<HTMLInputElement>(null)
  const isCustomColor = !PRESETS.some((p) => p.value.toLowerCase() === accentColor.toLowerCase())

  return (
    <div className="flex flex-col gap-5">
      <header>
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">
          Voreinstellungen
        </div>
        <h1 className="mt-2 text-[22px] font-semibold leading-tight text-white/95">
          Erscheinungsbild
        </h1>
      </header>

      {/* Schriftgröße */}
      <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        <SectionLabel>Schriftgröße</SectionLabel>
        <div className="mt-3 grid grid-cols-3 gap-2">
          {FONT_SIZES.map((size) => (
            <FontSizeCard
              key={size}
              size={size}
              active={fontSize === size}
              onClick={() => setFontSize(size)}
            />
          ))}
        </div>
        <p className="mt-3 text-[11px] text-white/30">
          Aktuelle Größe: {FONT_SIZE_PX[fontSize]}px — skaliert die gesamte Oberfläche.
        </p>
      </section>

      {/* Benutzerdefiniertes Thema */}
      <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        <SectionLabel>Benutzerdefiniertes Thema</SectionLabel>
        <input
          type="text"
          placeholder="Geben Sie Ihren Namen oder Titel ein"
          value={customThemeName}
          onChange={(e) => setCustomThemeName(e.target.value)}
          className="mt-3 w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2
                     text-[12px] text-white/80 placeholder:text-white/25 outline-none
                     focus:border-white/20 transition-colors"
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {PRESETS.map((p) => (
            <SwatchButton
              key={p.value}
              label={p.label}
              color={p.value}
              active={accentColor.toLowerCase() === p.value.toLowerCase()}
              onClick={() => setAccentColor(p.value)}
            />
          ))}
          <SwatchButton
            label="Eigene Farbe"
            color={accentColor}
            active={isCustomColor}
            onClick={() => colorInputRef.current?.click()}
            renderChild={<Plus className="h-3 w-3 text-white mix-blend-difference" />}
          />
        </div>
        <input
          ref={colorInputRef}
          type="color"
          value={accentColor}
          onChange={(e) => setAccentColor(e.target.value)}
          className="sr-only"
        />
      </section>

      <BackgroundSection
        backgroundSource={backgroundSource}
        setBackgroundSource={setBackgroundSource}
        ownBackgrounds={ownBackgrounds}
        addOwnBackground={addOwnBackground}
        removeOwnBackground={removeOwnBackground}
        backgroundImage={backgroundImage}
        setBackgroundImage={setBackgroundImage}
      />

      {/* Erscheinungsbild-Modus */}
      <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        <SectionLabel>Erscheinungsbild-Modus</SectionLabel>
        <div className="mt-3 grid grid-cols-3 gap-1 rounded-xl border border-white/8 bg-white/[0.02] p-1">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => setAppearanceMode(m.id)}
              className={cn(
                'flex items-center justify-center gap-1.5 rounded-lg py-2 text-[12px] font-medium transition-colors',
                appearanceMode === m.id
                  ? 'bg-white/10 text-white/90'
                  : 'text-white/40 hover:text-white/65',
              )}
            >
              {m.icon}
              {m.label}
            </button>
          ))}
        </div>
        {appearanceMode === 'auto' && (
          <p className="mt-2 text-[11px] text-white/30">
            Das Design passt sich automatisch an die Tageszeit an.
          </p>
        )}
      </section>
    </div>
  )
}
