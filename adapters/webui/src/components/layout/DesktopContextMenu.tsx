import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { useWindowStore } from '@/state/windowStore'
import { useUiStore } from '@/state/uiStore'
import { APP_REGISTRY } from '@/lib/contracts/appRegistry'
import { AppIcon } from '@/components/icons/AppIcon'
import { ImageOff } from 'lucide-react'
import { useTranslation } from '@/lib/i18n'

interface Props {
  x: number
  y: number
  onClose: () => void
}

const MENU_W = 210
const MENU_H_APPROX = 200

export function DesktopContextMenu({ x, y, onClose }: Props) {
  const { openWindow } = useWindowStore()
  const { backgroundImage, setBackgroundImage } = useUiStore()
  const { t } = useTranslation()

  // Stay within viewport
  const safeX = Math.min(x, window.innerWidth  - MENU_W - 8)
  const safeY = Math.min(y, window.innerHeight - MENU_H_APPROX - 8)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  function run(action: () => void) {
    action()
    onClose()
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.08 }}
      style={{ left: safeX, top: safeY, width: MENU_W, zIndex: 9999, position: 'fixed' }}
      className="glass border border-white/10 rounded-xl shadow-2xl overflow-hidden py-1 pointer-events-auto"
    >
      {/* Apps */}
      {APP_REGISTRY.map((app) => (
        <button
          key={app.id}
          onClick={() => run(() => openWindow(app.openArgs))}
          className="w-full flex items-center gap-3 px-3 py-2 text-sm text-white/70 hover:text-white hover:bg-white/8 transition-colors text-left"
        >
          <AppIcon name={app.iconName} className="w-4 h-4 flex-shrink-0" />
          <span>{app.label}</span>
        </button>
      ))}

      {/* Separator */}
      <div className="my-1 border-t border-white/8" />

      {/* Reset background */}
      <button
        onClick={() => run(() => setBackgroundImage(null))}
        disabled={!backgroundImage}
        className="w-full flex items-center gap-3 px-3 py-2 text-sm text-white/50 hover:text-white/80 hover:bg-white/8 transition-colors text-left disabled:opacity-30 disabled:pointer-events-none"
      >
        <ImageOff className="w-4 h-4 flex-shrink-0" />
        <span>{t('desktop.resetBackground')}</span>
      </button>
    </motion.div>
  )
}
