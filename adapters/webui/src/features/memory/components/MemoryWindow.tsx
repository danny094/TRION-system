import { useMemoryStore } from '../state/memoryStore'
import { MemorySidebar } from './MemorySidebar'
import { RecentView } from './views/RecentView'
import { SearchView } from './views/SearchView'
import { ConversationsView } from './views/ConversationsView'

export function MemoryWindow() {
  const view = useMemoryStore((s) => s.view)
  return (
    <div className="flex h-full w-full overflow-hidden bg-[#161618]">
      <MemorySidebar />
      <div className="flex-1 overflow-y-auto">
        {view === 'recent' ? <RecentView /> : null}
        {view === 'search' ? <SearchView /> : null}
        {view === 'conversations' ? <ConversationsView /> : null}
      </div>
    </div>
  )
}
