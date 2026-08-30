import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Square } from 'lucide-react'
import { useChatStore } from '../state/chatStore'
import { getActiveSession } from '../lib/sessionSelectors'
import { useTranslation } from '@/lib/i18n'

export function ChatInput() {
  const [input, setInput] = useState('')
  const { sessions, activeSessionId, sendMessage } = useChatStore()
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const activeSession = getActiveSession(sessions, activeSessionId)
  const isBusy = activeSession?.isBusy ?? false
  const { t } = useTranslation()

  const handleSend = () => {
    if (input.trim() && !isBusy) {
      void sendMessage(input.trim())
      setInput('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    // Auto-grow textarea
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }

  const canSend = input.trim().length > 0 && !isBusy

  return (
    <div className="px-4 pb-4 pt-3 shrink-0 border-t border-white/5">
      <div className="relative flex items-end gap-3">
        {/* Textarea */}
        <div className="flex-1 relative group">
          {/* Glow on focus */}
          <div className="absolute inset-0 rounded-2xl bg-primary/10 blur-md opacity-0 group-focus-within:opacity-100 transition-opacity duration-300 pointer-events-none -z-10" />
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={isBusy ? t('chat.replying') : t('chat.inputPlaceholder')}
            disabled={isBusy}
            rows={1}
            className="w-full bg-white/5 border border-white/10 group-focus-within:border-primary/30 rounded-2xl px-4 py-3 text-sm text-white/90 placeholder:text-white/25 focus:outline-none transition-colors resize-none leading-relaxed"
          />
        </div>

        {/* Send / Stop Button */}
        <AnimatePresence mode="wait">
          {isBusy ? (
            <motion.button
              key="stop"
              aria-label={t('chat.stop')}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="w-10 h-10 rounded-xl bg-red-500/20 border border-red-500/30 flex items-center justify-center text-red-400 hover:bg-red-500/30 transition-colors shrink-0 mb-0.5"
            >
              <Square className="w-4 h-4" />
            </motion.button>
          ) : (
            <motion.button
              key="send"
              aria-label={t('chat.send')}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              onClick={handleSend}
              disabled={!canSend}
              className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/30 flex items-center justify-center text-primary hover:bg-primary/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all shrink-0 mb-0.5 active:scale-95"
            >
              <Send className="w-4 h-4" />
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      <p className="text-[10px] text-white/15 text-center mt-2">
        {t('chat.disclaimer')}
      </p>
    </div>
  )
}
