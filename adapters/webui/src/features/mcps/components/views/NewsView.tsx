interface ChangelogEntry {
  kind: 'release' | 'update' | 'added' | 'fixed'
  version: string
  title: string
  description: string
  timestamp: string
}

// Editorial content — kept in source. When a CMS or release-notes feed is wired,
// the constant can be swapped for a fetcher returning the same shape.
const CHANGELOG: ChangelogEntry[] = [
  {
    kind: 'release', version: 'v1.0.0',
    title: 'MCP Installer 1.0 ships',
    description: 'Initial release: install via ZIP or GitHub, toggle servers live, clean uninstall.',
    timestamp: 'Today',
  },
  {
    kind: 'update', version: 'v0.9.4',
    title: 'Health-checks run on every install',
    description: 'Faster failure detection — broken manifests no longer block the installer queue.',
    timestamp: 'Yesterday',
  },
  {
    kind: 'added', version: 'v0.9.2',
    title: 'Pin servers to the TRION dock',
    description: 'Drag any installed MCP from the All-tab onto the dock for one-click toggling.',
    timestamp: '3 days ago',
  },
  {
    kind: 'fixed', version: 'v0.9.1',
    title: 'Symlink cleanup on uninstall',
    description: 'Removing a server no longer leaves behind dangling symlinks in ~/.trion/mcp.',
    timestamp: 'Last week',
  },
]

const BADGE_CLASSES: Record<ChangelogEntry['kind'], string> = {
  release: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/20',
  update:  'bg-sky-500/15 text-sky-300 border-sky-500/20',
  added:   'bg-purple-500/15 text-purple-300 border-purple-500/20',
  fixed:   'bg-white/8 text-white/65 border-white/12',
}

export function NewsView() {
  return (
    <div className="flex h-full flex-col gap-5">
      <header>
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">
          changelog
        </div>
        <h1 className="mt-2 text-[22px] font-semibold leading-tight text-white/95">News</h1>
        <p className="mt-2 text-[12px] text-white/55">
          What's new in the MCP Installer and supported servers.
        </p>
      </header>

      <div className="flex flex-col gap-2">
        {CHANGELOG.map((entry) => (
          <EntryRow key={entry.version} entry={entry} />
        ))}
      </div>
    </div>
  )
}

function EntryRow({ entry }: { entry: ChangelogEntry }) {
  return (
    <article className="grid grid-cols-[100px_1fr_auto] items-start gap-4 rounded-2xl border border-white/6 bg-white/[0.015] px-4 py-3.5">
      <div className="flex flex-col items-start gap-1.5">
        <span className={`rounded-md border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider ${BADGE_CLASSES[entry.kind]}`}>
          {entry.kind}
        </span>
        <span className="font-mono text-[10px] text-white/35">{entry.version}</span>
      </div>
      <div className="min-w-0">
        <div className="text-[13px] font-medium text-white/90">{entry.title}</div>
        <div className="mt-0.5 text-[11px] leading-relaxed text-white/50">{entry.description}</div>
      </div>
      <div className="shrink-0 text-[10px] text-white/35">{entry.timestamp}</div>
    </article>
  )
}
