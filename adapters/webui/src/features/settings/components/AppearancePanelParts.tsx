import { useRef } from 'react'
import { Plus, X } from 'lucide-react'
import { useTranslation } from '@/lib/i18n'
import { type BackgroundSource, type FontSize } from '@/state/uiStore'
import { cn } from '@/lib/utils'

const FONT_SIZE_LABEL_KEYS: Record<FontSize, string> = {
  sm: 'settings.fontSizeSmall',
  md: 'settings.fontSizeMedium',
  lg: 'settings.fontSizeLarge',
  xl: 'settings.fontSizeExtraLarge',
}

const BG_SOURCES: { id: BackgroundSource; label: string }[] = [
  { id: 'system', label: 'System' },
  { id: 'own', label: 'Eigene' },
]

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-white/50">{children}</div>
}

export function FontSizeCard({ size, active, onClick }: {
  size: FontSize
  active: boolean
  onClick: () => void
}) {
  const { t } = useTranslation()
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
      <span className="text-[11px]">{t(FONT_SIZE_LABEL_KEYS[size])}</span>
    </button>
  )
}

export function SwatchButton({ label, color, active, onClick, renderChild }: {
  label: string
  color: string
  active: boolean
  onClick: () => void
  renderChild?: React.ReactNode
}) {
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

interface BackgroundSectionProps {
  backgroundSource: BackgroundSource
  setBackgroundSource: (source: BackgroundSource) => void
  ownBackgrounds: string[]
  addOwnBackground: (dataUrl: string) => void
  removeOwnBackground: (index: number) => void
  backgroundImage: string | null
  setBackgroundImage: (dataUrl: string | null) => void
}

export function BackgroundSection(props: BackgroundSectionProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (loadEvent) => {
      const result = loadEvent.target?.result
      if (typeof result === 'string') {
        props.addOwnBackground(result)
        props.setBackgroundImage(result)
      }
    }
    reader.readAsDataURL(file)
    event.target.value = ''
  }

  return (
    <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
      <SectionLabel>Hintergrundbild</SectionLabel>
      <div className="mt-3 flex gap-1 rounded-xl border border-white/8 bg-white/[0.02] p-1">
        {BG_SOURCES.map((source) => (
          <button
            key={source.id}
            type="button"
            onClick={() => props.setBackgroundSource(source.id)}
            className={cn(
              'flex-1 rounded-lg py-1.5 text-[12px] font-medium transition-colors',
              props.backgroundSource === source.id ? 'bg-white/10 text-white/90' : 'text-white/40 hover:text-white/65',
            )}
          >
            {source.label}
          </button>
        ))}
      </div>
      {props.backgroundSource === 'own' && (
        <div className="mt-3 grid grid-cols-3 gap-2">
          {props.ownBackgrounds.map((image, index) => (
            <div key={index} className="group relative aspect-video overflow-hidden rounded-xl border border-white/10">
              <img
                src={image}
                alt=""
                onClick={() => props.setBackgroundImage(image)}
                className={cn(
                  'h-full w-full cursor-pointer object-cover transition-opacity',
                  props.backgroundImage === image ? 'ring-2 ring-white/50 ring-offset-1 ring-offset-black/40' : 'opacity-70 hover:opacity-100',
                )}
              />
              <button
                type="button"
                onClick={() => {
                  props.removeOwnBackground(index)
                  if (props.backgroundImage === image) props.setBackgroundImage(null)
                }}
                className="absolute right-1 top-1 hidden h-5 w-5 items-center justify-center rounded-full bg-black/60 text-white/80 group-hover:flex"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex aspect-video flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-white/15 text-white/30 transition-colors hover:border-white/25 hover:text-white/55"
          >
            <Plus className="h-4 w-4" />
            <span className="text-[10px]">Bild hochladen</span>
          </button>
        </div>
      )}
      {props.backgroundSource === 'system' && (
        <p className="mt-3 text-[11px] text-white/30">
          Verwendet das System-Hintergrundbild des Betriebssystems (wenn verfügbar).
        </p>
      )}
      <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleUpload} />
    </section>
  )
}
