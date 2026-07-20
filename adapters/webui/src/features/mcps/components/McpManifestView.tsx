import { useState } from 'react'
import { ChevronRight, FileJson } from 'lucide-react'
import { cn } from '@/lib/utils'

interface McpManifestViewProps {
  rawJson: string
}

export function McpManifestView({ rawJson }: McpManifestViewProps) {
  const [open, setOpen] = useState(false)

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-white/35 transition-colors hover:text-white/70"
      >
        <FileJson className="h-3.5 w-3.5" />
        Manifest inspizieren
        <ChevronRight
          className={cn('h-3.5 w-3.5 transition-transform', open && 'rotate-90')}
        />
      </button>
      {open && (
        <pre className="mt-3 overflow-x-auto rounded-2xl border border-white/8 bg-black/40 p-4 font-mono text-[11px] leading-relaxed text-white/55">
          {rawJson}
        </pre>
      )}
    </div>
  )
}
