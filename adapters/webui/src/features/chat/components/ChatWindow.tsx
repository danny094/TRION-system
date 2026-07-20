import { useState, useEffect, useRef } from 'react'
import { ChatMessageList } from './ChatMessageList'
import { ChatInput } from './ChatInput'
import { ChatHeader } from './ChatHeader'
import { ChatSessionSidebar } from './ChatSessionSidebar'

const AUTO_COLLAPSE_BREAKPOINT = 520 // px – auto-collapse when chat panel is narrower

export function ChatWindow() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [collapsed, setCollapsed] = useState(false)
  const userOverrideRef = useRef(false)

  // Auto-collapse based on container width — but respect user override
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const observer = new ResizeObserver(([entry]) => {
      if (userOverrideRef.current) return
      const width = entry.contentRect.width
      setCollapsed(width < AUTO_COLLAPSE_BREAKPOINT)
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  function handleToggle() {
    userOverrideRef.current = true
    setCollapsed((c) => !c)
  }

  return (
    <div ref={containerRef} className="flex h-full w-full overflow-hidden">
      <ChatSessionSidebar collapsed={collapsed} onToggle={handleToggle} />
      <div className="flex min-w-0 flex-1 flex-col">
        <ChatHeader />
        <ChatMessageList />
        <ChatInput />
      </div>
    </div>
  )
}
