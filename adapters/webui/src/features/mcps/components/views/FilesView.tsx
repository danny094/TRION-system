import { useMemo, useState } from 'react'
import { Search, Upload, Plus, ChevronRight, Folder } from 'lucide-react'

// Mock listing — backend wiring (GET /api/mcp/files) is delivered in the next step.
// Keep the shape stable so the fetch hook can replace this constant 1:1.
interface FileEntry {
  name: string
  modified: string
  size: string
  tint: FileTint
}

type FileTint = 'purple' | 'teal' | 'rose' | 'amber'

const MOCK_FILES: FileEntry[] = [
  { name: 'skill-server.config.yaml',     modified: 'today',      size: '1.2 KB', tint: 'purple' },
  { name: 'manifest.json',                modified: 'today',      size: '428 B',  tint: 'purple' },
  { name: 'container-manager.dockerfile', modified: 'yesterday',  size: '2.1 KB', tint: 'teal' },
  { name: 'memory-schema.sql',            modified: '3 days ago', size: '5.8 KB', tint: 'teal' },
  { name: 'secrets.env',                  modified: '1 week ago', size: '284 B',  tint: 'rose' },
]

const TINT_CLASSES: Record<FileTint, string> = {
  purple: 'from-purple-500/30 to-purple-500/10 text-purple-200',
  teal:   'from-teal-500/30 to-teal-500/10 text-teal-200',
  rose:   'from-rose-500/30 to-rose-500/10 text-rose-200',
  amber:  'from-amber-500/30 to-amber-500/10 text-amber-200',
}

const INSTALL_PATH = '~/.trion/mcp'

export function FilesView() {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return MOCK_FILES
    return MOCK_FILES.filter((f) => f.name.toLowerCase().includes(q))
  }, [query])

  return (
    <div className="flex h-full flex-col gap-5">
      <header className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">
            {INSTALL_PATH}
          </div>
          <h1 className="mt-2 text-[22px] font-semibold leading-tight text-white/95">
            Files
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/8 bg-white/[0.03] px-3 py-1.5 text-[11px] text-white/75 transition hover:bg-white/[0.06] hover:text-white/95"
          >
            <Upload className="h-3.5 w-3.5" />
            Upload
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/12 bg-white/8 px-3 py-1.5 text-[11px] font-medium text-white/90 transition hover:bg-white/12"
          >
            <Plus className="h-3.5 w-3.5" />
            New
          </button>
        </div>
      </header>

      <SearchBar value={query} onChange={setQuery} />

      <div className="flex-1 overflow-hidden rounded-2xl border border-white/6 bg-white/[0.015]">
        <div className="grid shrink-0 grid-cols-[1fr_120px_80px_40px] gap-3 border-b border-white/6 px-4 py-2.5 text-[10px] uppercase tracking-[0.14em] text-white/35">
          <span>Name</span>
          <span>Modified</span>
          <span>Size</span>
          <span />
        </div>
        {filtered.length === 0 ? (
          <div className="px-5 py-10 text-center text-[12px] text-white/35">
            {query ? 'No files match your search.' : 'No files yet.'}
          </div>
        ) : (
          <div className="overflow-y-auto">
            {filtered.map((file) => <FileRow key={file.name} file={file} />)}
          </div>
        )}
      </div>
    </div>
  )
}

function SearchBar({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-2 rounded-full border border-white/8 bg-white/[0.03] px-3 py-1.5 w-72">
      <Search className="h-3.5 w-3.5 shrink-0 text-white/35" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search files…"
        className="flex-1 bg-transparent text-[12px] text-white/85 placeholder:text-white/30 focus:outline-none"
      />
      <kbd className="rounded bg-white/8 px-1 py-0.5 text-[9px] text-white/45">⌘K</kbd>
    </div>
  )
}

function FileRow({ file }: { file: FileEntry }) {
  return (
    <button
      type="button"
      className="grid w-full grid-cols-[1fr_120px_80px_40px] items-center gap-3 border-b border-white/4 px-4 py-2.5 text-left transition last:border-b-0 hover:bg-white/[0.02]"
    >
      <div className="flex min-w-0 items-center gap-3">
        <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${TINT_CLASSES[file.tint]}`}>
          <Folder className="h-3.5 w-3.5" />
        </div>
        <span className="truncate font-mono text-[12px] text-white/85">{file.name}</span>
      </div>
      <div className="text-[11px] text-white/45">{file.modified}</div>
      <div className="font-mono text-[11px] text-white/45">{file.size}</div>
      <div className="flex justify-end">
        <div className="flex h-6 w-6 items-center justify-center rounded-md border border-white/8 bg-white/[0.02] text-white/35">
          <ChevronRight className="h-3 w-3" />
        </div>
      </div>
    </button>
  )
}
