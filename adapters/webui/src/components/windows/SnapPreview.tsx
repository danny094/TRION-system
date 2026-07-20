import { createPortal } from 'react-dom'
import { motion } from 'framer-motion'

export type SnapZone = 'left' | 'right' | 'top'

const SNAP_STYLE: Record<SnapZone, React.CSSProperties> = {
  left:  { left: 0,    top: 0, width: '50%',  height: 'calc(100vh - 120px)' },
  right: { right: 0,   top: 0, width: '50%',  height: 'calc(100vh - 120px)' },
  top:   { left: 0,    top: 0, right: 0,      height: 'calc(100vh - 120px)' },
}

export function SnapPreview({ zone }: { zone: SnapZone }) {
  return createPortal(
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.12 }}
      style={{ ...SNAP_STYLE[zone], position: 'fixed', zIndex: 9999, pointerEvents: 'none' }}
      className="bg-primary/10 border-2 border-primary/30 rounded-2xl"
    />,
    document.body
  )
}
