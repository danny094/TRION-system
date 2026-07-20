import { Inbox } from 'lucide-react'
import type { McpSummary } from '@/lib/contracts/mcp'
import { McpListItem } from './McpListItem'

interface McpsListViewProps {
  mcps: McpSummary[]
  selectedName: string | null
  onSelect: (name: string) => void
}

export function McpsListView({ mcps, selectedName, onSelect }: McpsListViewProps) {
  if (mcps.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-white/30 select-none">
        <Inbox className="h-8 w-8 opacity-60" />
        <span className="text-xs uppercase tracking-widest">Keine MCPs installiert</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      {mcps.map((mcp, index) => (
        <McpListItem
          key={mcp.name}
          mcp={mcp}
          index={index}
          active={selectedName === mcp.name}
          onSelect={() => onSelect(mcp.name)}
        />
      ))}
    </div>
  )
}
