import { LayoutGrid, MessageSquare } from 'lucide-react'
import { useWindowStore } from '@/state/windowStore'
import { getApp } from '@/lib/contracts/appRegistry'

export function LaunchpadButton() {
  const { openWindow } = useWindowStore()
  const launchpadApp = getApp('launchpad')
  const chatApp = getApp('chat')

  return (
    <div className="fixed bottom-6 left-6 z-50 flex gap-4">
      {/* Launchpad / Home */}
      <button
        id="btn-launchpad"
        onClick={() => launchpadApp && openWindow(launchpadApp.openArgs)}
        className="w-14 h-14 rounded-[1.25rem] glass flex items-center justify-center text-white/70 hover:text-primary hover:bg-white/10 transition-all shadow-lg hover:shadow-[0_0_20px_rgba(234,179,8,0.3)] active:scale-95 group"
      >
        <LayoutGrid className="w-6 h-6 group-hover:scale-110 transition-transform" />
      </button>

      {/* Chat App */}
      <button
        id="btn-chat"
        onClick={() => chatApp && openWindow(chatApp.openArgs)}
        className="w-14 h-14 rounded-[1.25rem] glass flex items-center justify-center text-white/70 hover:text-primary hover:bg-white/10 transition-all shadow-lg hover:shadow-[0_0_20px_rgba(234,179,8,0.3)] active:scale-95 group"
      >
        <MessageSquare className="w-6 h-6 group-hover:scale-110 transition-transform" />
      </button>
    </div>
  )
}
