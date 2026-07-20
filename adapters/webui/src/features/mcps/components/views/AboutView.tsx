import { GitBranch, Archive, ChevronRight } from 'lucide-react'

interface AboutViewProps {
  installedCount: number
  activeCount: number
  offlineCount: number
}

const BUILD_NUMBER = 24
const FEATURES = [
  'Install MCPs from ZIP or GitHub in one step.',
  'Toggle servers on / off without restarting TRION.',
  'Inspect logs, manifests and config files per server.',
  'Roll back or remove cleanly — no orphaned files.',
]

export function AboutView({ installedCount, activeCount, offlineCount }: AboutViewProps) {
  return (
    <div className="flex h-full flex-col gap-6">
      <header>
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">
          v 1.0 · build {BUILD_NUMBER}
        </div>
        <h1 className="mt-2 text-[22px] font-semibold leading-tight text-white/95">
          Welcome to the MCP Installer
        </h1>
        <p className="mt-2 max-w-[560px] text-[13px] leading-relaxed text-white/55">
          A small, focused tool to install, toggle and remove
          Model-Context-Protocol servers for TRION.
        </p>
      </header>

      <div className="grid flex-1 grid-cols-2 gap-3">
        <SupportedSourcesCard
          installedCount={installedCount}
          activeCount={activeCount}
          offlineCount={offlineCount}
        />
        <WhatItDoesCard />
      </div>
    </div>
  )
}

interface SourcesProps {
  installedCount: number
  activeCount: number
  offlineCount: number
}

function SupportedSourcesCard({ installedCount, activeCount, offlineCount }: SourcesProps) {
  return (
    <section className="flex flex-col rounded-2xl border border-white/6 bg-white/[0.02] p-4">
      <div className="text-[12px] text-white/55">Supported sources</div>

      <div className="mt-3 flex flex-col gap-2">
        <SourceRow
          icon={<GitBranch className="h-3.5 w-3.5" />}
          title="GitHub repository"
          subtitle="public or private — paste any tree URL"
        />
        <SourceRow
          icon={<Archive className="h-3.5 w-3.5" />}
          title="ZIP / TAR archive"
          subtitle="drop into the install pane or browse from disk"
        />
      </div>

      <div className="mt-auto flex items-end gap-6 pt-6">
        <Stat value={installedCount} label="Installed" />
        <Stat value={activeCount} label="Active" tint="emerald" />
        <Stat value={offlineCount} label="Offline" tint="muted" />
      </div>
    </section>
  )
}

interface SourceRowProps {
  icon: React.ReactNode
  title: string
  subtitle: string
}

function SourceRow({ icon, title, subtitle }: SourceRowProps) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-white/5 bg-white/[0.015] px-3 py-2.5">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/8 text-white/70">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[12px] font-medium text-white/85">{title}</div>
        <div className="mt-0.5 truncate text-[11px] text-white/40">{subtitle}</div>
      </div>
      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-white/25" />
    </div>
  )
}

interface StatProps {
  value: number
  label: string
  tint?: 'emerald' | 'muted'
}

function Stat({ value, label, tint }: StatProps) {
  const valueColor =
    tint === 'emerald' ? 'text-emerald-300' : tint === 'muted' ? 'text-white/55' : 'text-white/90'
  return (
    <div>
      <div className={`text-[20px] font-semibold leading-none tabular-nums ${valueColor}`}>
        {value}
      </div>
      <div className="mt-1.5 text-[10px] uppercase tracking-[0.14em] text-white/35">
        {label}
      </div>
    </div>
  )
}

function WhatItDoesCard() {
  return (
    <section className="flex flex-col rounded-2xl border border-white/6 bg-white/[0.02] p-4">
      <div className="text-[12px] text-white/55">What it does</div>

      <ul className="mt-3 flex flex-col gap-2">
        {FEATURES.map((feature) => (
          <li key={feature} className="flex items-start gap-2.5">
            <span className="mt-1.5 inline-block h-1 w-1 shrink-0 rounded-full bg-emerald-400/80" />
            <span className="text-[12px] leading-relaxed text-white/70">{feature}</span>
          </li>
        ))}
      </ul>

      <p className="mt-auto pt-6 text-[11px] leading-relaxed text-white/35">
        Tailored to the TRION runtime — settings, paths and lifecycle hooks
        resolve automatically.
      </p>
    </section>
  )
}
