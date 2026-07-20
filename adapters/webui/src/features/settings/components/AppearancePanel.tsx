import { useRef } from 'react'
import { Sun, Moon, SunMoon, Plus, X } from 'lucide-react'
import {
  useUiStore,
  FONT_SIZE_PX,
  FONT_SIZE_LABELS,
  type FontSize,
  type AppearanceMode,
  type BackgroundSource,
} from '@/state/uiStore'
import { cn } from '@/lib/utils'

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

const BG_SOURCES: { id: BackgroundSource; label: string }[] = [
  { id: 'system', label: 'System' },
  { id: 'own',    label: 'Eigene' },
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
  const fileInputRef  = useRef<HTMLInputElement>(null)
  const isCustomColor = !PRESETS.some((p) => p.value.toLowerCase() === accentColor.toLowerCase())

  function handleBgUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const result = ev.target?.result
      if (typeof result === 'string') {
        addOwnBackground(result)
        setBackgroundImage(result)
      }
    }
    reader.readAsDataURL(file)
    e.target.value = ''
  }

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

      {/* Hintergrundbild */}
      <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        <SectionLabel>Hintergrundbild</SectionLabel>
        <div className="mt-3 flex gap-1 rounded-xl border border-white/8 bg-white/[0.02] p-1">
          {BG_SOURCES.map((src) => (
            <button
              key={src.id}
              type="button"
              onClick={() => setBackgroundSource(src.id)}
              className={cn(
                'flex-1 rounded-lg py-1.5 text-[12px] font-medium transition-colors',
                backgroundSource === src.id
                  ? 'bg-white/10 text-white/90'
                  : 'text-white/40 hover:text-white/65',
              )}
            >
              {src.label}
            </button>
          ))}
        </div>

        {backgroundSource === 'own' && (
          <div className="mt-3 grid grid-cols-3 gap-2">
            {ownBackgrounds.map((img, idx) => (
              <div key={idx} className="group relative aspect-video overflow-hidden rounded-xl border border-white/10">
                <img
                  src={img}
                  alt=""
                  onClick={() => setBackgroundImage(img)}
                  className={cn(
                    'h-full w-full cursor-pointer object-cover transition-opacity',
                    backgroundImage === img ? 'ring-2 ring-white/50 ring-offset-1 ring-offset-black/40' : 'opacity-70 hover:opacity-100',
                  )}
                />
                <button
                  type="button"
                  onClick={() => {
                    removeOwnBackground(idx)
                    if (backgroundImage === img) setBackgroundImage(null)
                  }}
                  className="absolute right-1 top-1 hidden h-5 w-5 items-center justify-center
                             rounded-full bg-black/60 text-white/80 group-hover:flex"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex aspect-video flex-col items-center justify-center gap-1 rounded-xl
                         border border-dashed border-white/15 text-white/30
                         transition-colors hover:border-white/25 hover:text-white/55"
            >
              <Plus className="h-4 w-4" />
              <span className="text-[10px]">Bild hochladen</span>
            </button>
          </div>
        )}

        {backgroundSource === 'system' && (
          <p className="mt-3 text-[11px] text-white/30">
            Verwendet das System-Hintergrundbild des Betriebssystems (wenn verfügbar).
          </p>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleBgUpload}
        />
      </section>

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

/* ── Sub-components ───────────────────────────────────────────── */

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-white/50">
      {children}
    </div>
  )
}

interface FontSizeCardProps {
  size: FontSize
  active: boolean
  onClick: () => void
}

function FontSizeCard({ size, active, onClick }: FontSizeCardProps) {
  const sizeMap: Record<FontSize, string> = { lg: 'text-4xl', md: 'text-2xl', sm: 'text-xl', xl: 'text-5xl' }
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex flex-col items-center gap-2 rounded-xl border py-3 transition-colors',
        active
          ? 'border-white/25 bg-white/[0.06] text-white/95'
          : 'border-white/8 text-white/40 hover:border-white/15 hover:text-white/70',
      )}
    >
      <span className={cn('font-semibold leading-none', sizeMap[size])}>Aa</span>
      <span className="text-[11px]">{FONT_SIZE_LABELS[size]}</span>
    </button>
  )
}

interface SwatchButtonProps {
  label: string
  color: string
  active: boolean
  onClick: () => void
  renderChild?: React.ReactNode
}

function SwatchButton({ label, color, active, onClick, renderChild }: SwatchButtonProps) {
  return (
    <button
      type="button"
      title={label}
      onClick={onClick}
      className={cn(
        'flex h-8 w-8 items-center justify-center rounded-full border-2 transition-transform duration-150 hover:scale-110',
        active ? 'scale-110 border-white/55' : 'border-white/15 hover:border-white/35',
      )}
      style={{ backgroundColor: color }}
    >
      {renderChild}
    </button>
  )
}
