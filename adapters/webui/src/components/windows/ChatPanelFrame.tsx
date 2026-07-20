import { motion } from 'framer-motion'
import { X, Maximize2, Minimize2, PanelRight } from 'lucide-react'
import { useWindowStore, type WindowState } from '@/state/windowStore'
import { ChatWindow } from '@/features/chat/components/ChatWindow'
import { cn } from '@/lib/utils'

interface ChatPanelFrameProps {
  windowState: WindowState
}

export function ChatPanelFrame({ windowState }: ChatPanelFrameProps) {
  const { closeWindow, setDisplayMode, focusWindow } = useWindowStore()
  const isFullscreen = windowState.displayMode === 'fullscreen'

  return (
    <motion.div
      layout
      layoutId={`chat-panel-${windowState.windowId}`}
      onPointerDown={() => focusWindow(windowState.windowId)}
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 60 }}
      transition={{ type: 'spring', stiffness: 340, damping: 32 }}
      style={{ zIndex: windowState.zIndex }}
      className={cn(
        'fixed flex flex-col overflow-hidden pointer-events-auto',
        isFullscreen
          ? 'inset-0 rounded-none'
          : 'right-5 top-5 bottom-24 w-[420px] rounded-2xl'
      )}
    >
      {/* Glass background */}
      <div className="absolute inset-0 bg-[#0d0d10]/85 backdrop-blur-3xl border border-white/10 rounded-[inherit] pointer-events-none" />

      {/* Subtle glow edge */}
      <div className="absolute inset-0 rounded-[inherit] shadow-[0_0_60px_rgba(234,179,8,0.06)] pointer-events-none" />

      {/* Content */}
      <div className="relative z-10 flex flex-col h-full">
        <ChatWindow />
      </div>

      {/* Floating Controls (top-right corner) */}
      <div className="absolute top-3 right-3 flex items-center gap-1 z-20">
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setDisplayMode(
            windowState.windowId,
            isFullscreen ? 'panel' : 'fullscreen'
          )}
          className="w-7 h-7 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center text-white/40 hover:text-white/70 transition-colors"
        >
          {isFullscreen
            ? <Minimize2 className="w-3.5 h-3.5" />
            : <Maximize2 className="w-3.5 h-3.5" />
          }
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setDisplayMode(windowState.windowId, 'panel')}
          className="w-7 h-7 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center text-white/40 hover:text-white/70 transition-colors"
          title="Als Panel"
        >
          <PanelRight className="w-3.5 h-3.5" />
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => closeWindow(windowState.windowId)}
          className="w-7 h-7 rounded-lg bg-white/5 hover:bg-red-500/20 border border-white/10 hover:border-red-500/30 flex items-center justify-center text-white/40 hover:text-red-400 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </motion.button>
      </div>
    </motion.div>
  )
}
