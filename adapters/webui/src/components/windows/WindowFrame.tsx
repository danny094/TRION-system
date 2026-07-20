import { useRef, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { X, Minus, Maximize2, Minimize2 } from 'lucide-react'
import { useWindowStore, type WindowState } from '@/state/windowStore'
import { ResizeHandles } from '@/components/windows/ResizeHandles'
import { SnapPreview, type SnapZone } from '@/components/windows/SnapPreview'
import { cn } from '@/lib/utils'

const DOCK_ZONE = 120
const SNAP_EDGE = 40

interface WindowFrameProps {
  windowState: WindowState
  children: React.ReactNode
}

export function WindowFrame({ windowState, children }: WindowFrameProps) {
  const { closeWindow, focusWindow, updateWindow } = useWindowStore()

  const [pos, setPos] = useState({
    x: windowState.position?.x ?? window.innerWidth * 0.1,
    y: windowState.position?.y ?? window.innerHeight * 0.1,
  })
  const [size, setSize] = useState({
    width: windowState.size?.width ?? 600,
    height: windowState.size?.height ?? 400,
  })
  const [snapZone, setSnapZone] = useState<SnapZone | null>(null)
  const snapZoneRef = useRef<SnapZone | null>(null)
  const dragState = useRef<{ startX: number; startY: number; originX: number; originY: number } | null>(null)

  const isMaximized = windowState.maximized
  const displayPos  = isMaximized ? { x: 0, y: 0 } : pos
  const displaySize = isMaximized
    ? { width: window.innerWidth, height: window.innerHeight - DOCK_ZONE }
    : size

  const handleResize = useCallback(
    (newPos: { x: number; y: number }, newSize: { width: number; height: number }) => {
      setPos(newPos)
      setSize(newSize)
    },
    []
  )

  const handleTitlePointerDown = useCallback((e: React.PointerEvent) => {
    if (isMaximized) return
    e.preventDefault()
    focusWindow(windowState.windowId)
    dragState.current = { startX: e.clientX, startY: e.clientY, originX: pos.x, originY: pos.y }

    const onMove = (ev: PointerEvent) => {
      if (!dragState.current) return
      setPos({
        x: dragState.current.originX + ev.clientX - dragState.current.startX,
        y: dragState.current.originY + ev.clientY - dragState.current.startY,
      })
      const zone: SnapZone | null =
        ev.clientX < SNAP_EDGE ? 'left'
        : ev.clientX > window.innerWidth - SNAP_EDGE ? 'right'
        : ev.clientY < SNAP_EDGE ? 'top'
        : null
      snapZoneRef.current = zone
      setSnapZone(zone)
    }

    const onUp = () => {
      dragState.current = null
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
      const zone = snapZoneRef.current
      snapZoneRef.current = null
      setSnapZone(null)
      if (zone === 'left') {
        setPos({ x: 0, y: 0 })
        setSize({ width: window.innerWidth / 2, height: window.innerHeight - DOCK_ZONE })
      } else if (zone === 'right') {
        setPos({ x: window.innerWidth / 2, y: 0 })
        setSize({ width: window.innerWidth / 2, height: window.innerHeight - DOCK_ZONE })
      } else if (zone === 'top') {
        updateWindow(windowState.windowId, {
          maximized: true,
          position: { x: pos.x, y: pos.y },
          size: { width: size.width, height: size.height },
        })
      }
    }

    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)
  }, [isMaximized, focusWindow, windowState.windowId, pos.x, pos.y, size.width, size.height, updateWindow])

  function toggleMaximize() {
    if (isMaximized) {
      updateWindow(windowState.windowId, { maximized: false })
    } else {
      updateWindow(windowState.windowId, {
        maximized: true,
        position: { x: pos.x, y: pos.y },
        size: { width: size.width, height: size.height },
      })
    }
  }

  function minimize() {
    updateWindow(windowState.windowId, { minimized: true })
  }

  return (
    <>
      {snapZone && <SnapPreview zone={snapZone} />}

      <motion.div
        onPointerDown={() => focusWindow(windowState.windowId)}
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        style={{
          zIndex: windowState.zIndex,
          width: displaySize.width,
          height: displaySize.height,
          left: displayPos.x,
          top: displayPos.y,
          position: 'absolute',
        }}
        className={cn(
          "flex flex-col glass border border-white/10 shadow-2xl overflow-hidden backdrop-blur-3xl pointer-events-auto transition-[border-radius] duration-200",
          isMaximized ? "rounded-none" : "rounded-2xl",
          windowState.focused ? "border-white/20 shadow-[0_8px_32px_rgba(234,179,8,0.15)]" : "opacity-80"
        )}
      >
        {/* Title Bar */}
        <div
          onPointerDown={handleTitlePointerDown}
          onDoubleClick={toggleMaximize}
          className={cn(
            "h-12 flex items-center justify-between px-4 border-b border-white/5 bg-white/5 hover:bg-white/10 transition-colors select-none",
            isMaximized ? "cursor-default" : "cursor-move"
          )}
        >
          <div className="text-sm font-medium text-white/80">{windowState.title}</div>
          <div className="flex items-center gap-2" onPointerDown={(e) => e.stopPropagation()}>
            <button onClick={minimize} className="w-7 h-7 rounded-full hover:bg-white/10 flex items-center justify-center text-white/50 hover:text-white transition-colors">
              <Minus className="w-3.5 h-3.5" />
            </button>
            <button onClick={toggleMaximize} className="w-7 h-7 rounded-full hover:bg-white/10 flex items-center justify-center text-white/50 hover:text-white transition-colors">
              {isMaximized ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
            <button onClick={() => closeWindow(windowState.windowId)} className="w-7 h-7 rounded-full hover:bg-red-500/20 hover:text-red-400 flex items-center justify-center text-white/50 transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-auto bg-black/40">{children}</div>

        {!isMaximized && <ResizeHandles pos={pos} size={size} onResize={handleResize} />}
      </motion.div>
    </>
  )
}
