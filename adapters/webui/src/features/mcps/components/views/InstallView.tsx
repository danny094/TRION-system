import { useRef, useState, type DragEvent } from 'react'
import { Upload, GitBranch } from 'lucide-react'
import { cn } from '@/lib/utils'

interface InstallViewProps {
  installPath: string
  onPickFile: (file: File) => void
  onOpenPicker: () => void
}

export function InstallView({ installPath, onPickFile, onOpenPicker }: InstallViewProps) {
  const [autoEnable, setAutoEnable] = useState(true)
  const [healthCheck, setHealthCheck] = useState(false)
  const [pinToDock, setPinToDock] = useState(false)

  return (
    <div className="flex h-full flex-col gap-5">
      <header>
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">
          add a server
        </div>
        <h1 className="mt-2 text-[22px] font-semibold leading-tight text-white/95">
          Install MCP
        </h1>
        <p className="mt-2 text-[12px] text-white/55">
          Drop an archive, browse from disk, or paste a GitHub URL.
        </p>
      </header>

      <div className="grid flex-1 grid-cols-2 gap-3">
        <DropZone onFile={onPickFile} onClick={onOpenPicker} />
        <GitHubCard />
      </div>

      <FooterBar
        autoEnable={autoEnable} setAutoEnable={setAutoEnable}
        healthCheck={healthCheck} setHealthCheck={setHealthCheck}
        pinToDock={pinToDock} setPinToDock={setPinToDock}
        installPath={installPath}
      />
    </div>
  )
}

function DropZone({ onFile, onClick }: { onFile: (file: File) => void; onClick: () => void }) {
  const [hover, setHover] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setHover(false)
    const file = e.dataTransfer.files?.[0]
    if (file) onFile(file)
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setHover(true) }}
      onDragLeave={() => setHover(false)}
      onDrop={handleDrop}
      onClick={onClick}
      className={cn(
        'flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border border-dashed bg-white/[0.015] p-6 transition',
        hover ? 'border-white/40 bg-white/[0.04]' : 'border-white/12 hover:border-white/20 hover:bg-white/[0.025]',
      )}
    >
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/8 text-white/75">
        <Upload className="h-5 w-5" />
      </div>
      <div className="text-center">
        <div className="text-[13px] font-medium text-white/85">Drop a ZIP or TAR archive</div>
        <div className="mt-0.5 text-[11px] text-white/45">
          or <span className="text-white/70 underline-offset-2 hover:underline">browse from disk</span>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-1.5">
        {['.zip', '.tar', '.tar.gz'].map((ext) => (
          <span key={ext} className="rounded-md bg-white/6 px-1.5 py-0.5 font-mono text-[10px] text-white/55">{ext}</span>
        ))}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".zip,.tar,.tar.gz,.tgz"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f) }}
      />
    </div>
  )
}

function GitHubCard() {
  const [repo, setRepo] = useState('')
  const [branch, setBranch] = useState('')
  return (
    <div className="flex flex-col rounded-2xl border border-white/6 bg-white/[0.02] p-4">
      <div className="flex items-center gap-2">
        <GitBranch className="h-3.5 w-3.5 text-white/70" />
        <span className="text-[12px] font-medium text-white/85">Install from GitHub</span>
        <span className="ml-auto rounded-full bg-white/6 px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-white/40">soon</span>
      </div>
      <p className="mt-1 text-[11px] text-white/45">
        Paste any repository URL. Branch or tag is parsed from the path.
      </p>

      <div className="mt-3 flex items-center gap-1.5 rounded-xl border border-white/8 bg-black/20 px-2 py-1.5">
        <span className="font-mono text-[10px] text-white/35">https://github.com/</span>
        <input
          type="text"
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="trion/skill-server"
          className="min-w-0 flex-1 bg-transparent font-mono text-[11px] text-white/90 placeholder:text-white/30 focus:outline-none"
        />
        <input
          type="text"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          placeholder="@main"
          className="w-14 bg-transparent font-mono text-[10px] text-white/55 placeholder:text-white/25 focus:outline-none"
        />
        <button
          type="button"
          disabled
          title="Backend coming soon"
          className="rounded-md bg-sky-500/85 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-white shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50 hover:bg-sky-400"
        >
          Install
        </button>
      </div>

      <div className="mt-auto pt-4 text-[10px] text-white/35">
        <span className="text-white/30">Recent:</span>{' '}
        <span className="text-white/55">trion/web-fetch</span>
        <span className="text-white/30">, </span>
        <span className="text-white/55">trion/fs-bridge</span>
      </div>
    </div>
  )
}

interface FooterBarProps {
  autoEnable: boolean; setAutoEnable: (v: boolean) => void
  healthCheck: boolean; setHealthCheck: (v: boolean) => void
  pinToDock: boolean; setPinToDock: (v: boolean) => void
  installPath: string
}

function FooterBar({ autoEnable, setAutoEnable, healthCheck, setHealthCheck, pinToDock, setPinToDock, installPath }: FooterBarProps) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-white/6 bg-white/[0.015] px-4 py-2.5 text-[11px] text-white/55">
      <div className="flex items-center gap-5">
        <ToggleOption label="Auto-enable after install" on={autoEnable} onClick={() => setAutoEnable(!autoEnable)} />
        <ToggleOption label="Run health-check"          on={healthCheck} onClick={() => setHealthCheck(!healthCheck)} />
        <ToggleOption label="Pin to dock"               on={pinToDock} onClick={() => setPinToDock(!pinToDock)} />
      </div>
      <div className="text-[10px] text-white/35">
        Install path: <span className="font-mono text-white/55">{installPath}</span>
      </div>
    </div>
  )
}

function ToggleOption({ label, on, onClick }: { label: string; on: boolean; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="flex items-center gap-2 transition hover:text-white/85">
      <span className={cn(
        'relative h-3 w-6 rounded-full transition-colors',
        on ? 'bg-emerald-500/75' : 'bg-white/12',
      )}>
        <span className={cn(
          'absolute top-0.5 h-2 w-2 rounded-full bg-white shadow-sm transition-transform',
          on ? 'translate-x-3.5' : 'translate-x-0.5',
        )} />
      </span>
      <span className={on ? 'text-white/85' : 'text-white/45'}>{label}</span>
    </button>
  )
}
