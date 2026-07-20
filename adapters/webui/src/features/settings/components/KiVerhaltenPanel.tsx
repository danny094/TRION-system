import { Brain, ChevronRight, Loader2, RefreshCw, Zap, User, Layers, Clock, Shield, GitBranch } from 'lucide-react'
import { useState } from 'react'
import { useAutonomyProfile } from '@/features/settings/useAutonomyProfile'
import { useMemoryDefaults } from '@/features/settings/useMemoryDefaults'
import type {
  AutonomyMode,
  ErrorBehavior,
  LoopSensitivity,
  PlanningDepth,
  WaitBehavior,
} from '@/features/settings/autonomyApi'
import type { MemoryMode } from '@/features/settings/memoryDefaultsApi'
import { cn } from '@/lib/utils'
import { ArbeitsmodusPanel } from './views/ki/ArbeitsmodusPanel'
import { PlanungstiefePanel } from './views/ki/PlanungstiefePanel'
import { WarteVerhaltenPanel } from './views/ki/WarteVerhaltenPanel'
import { SicherheitsebenePanel } from './views/ki/SicherheitsebenePanel'
import { FehlerVerhaltenPanel } from './views/ki/FehlerVerhaltenPanel'
import { SchleifenerkennungPanel } from './views/ki/SchleifenerkennungPanel'
import { PersonaPanel } from './views/ki/PersonaPanel'
import { MemoryPanel } from './views/ki/MemoryPanel'

type KiView = 'list' | 'persona' | 'arbeitsmodus' | 'planungstiefe' | 'warteverhalten' | 'sicherheit' | 'fehler' | 'schleifen' | 'memory'

const MEMORY_LABELS: Record<MemoryMode, string> = {
  global_enabled: 'Ja, dauerhaft',
  conversation_only: 'Nur diese Unterhaltung',
  disabled: 'Aus',
}

function memoryLabel(mode: MemoryMode, doNotRemember: boolean): string {
  if (doNotRemember) return MEMORY_LABELS.disabled
  return MEMORY_LABELS[mode]
}

const AUTONOMY_LABELS: Record<AutonomyMode, string> = { manuell:'Manuell', halbautomatisch:'Halbautomatisch', autonom:'Autonom' }
const DEPTH_LABELS: Record<PlanningDepth, string> = { schnell:'Schnell', normal:'Normal', 'gründlich':'Gründlich', unbegrenzt:'Unbegrenzt' }
const WAIT_LABELS: Record<WaitBehavior, string> = { sofort:'Sofort stopp', '30sek':'30 Sek', '2min':'2 Min', immer:'Immer' }
const ERROR_LABELS: Record<ErrorBehavior, string> = { retry:'Retry', ask:'Fragen', abort:'Abbrechen' }

export function KiVerhaltenPanel() {
  const [view, setView] = useState<KiView>('list')
  const { profile, loading, savingField, error, status, load, updateField } = useAutonomyProfile()
  const { defaults: memoryDefaults } = useMemoryDefaults()

  const back = () => setView('list')
  const askBeforeTools = profile.safety_level === 'erhöht'

  if (view === 'persona') {
    return <PersonaPanel onBack={back} />
  }
  if (view === 'memory') {
    return <MemoryPanel onBack={back} />
  }
  if (view === 'arbeitsmodus') {
    return (
      <ArbeitsmodusPanel
        value={profile.mode as AutonomyMode}
        onChange={(value) => void updateField('mode', value)}
        onBack={back}
      />
    )
  }
  if (view === 'planungstiefe') {
    return (
      <PlanungstiefePanel
        value={profile.planning_depth as PlanningDepth}
        onChange={(value) => void updateField('planning_depth', value)}
        onBack={back}
      />
    )
  }
  if (view === 'warteverhalten') {
    return (
      <WarteVerhaltenPanel
        value={profile.wait_behavior as WaitBehavior}
        onChange={(value) => void updateField('wait_behavior', value)}
        onBack={back}
      />
    )
  }
  if (view === 'sicherheit') {
    return (
      <SicherheitsebenePanel
        askBeforeTools={askBeforeTools}
        onToggle={() => void updateField('safety_level', askBeforeTools ? 'standard' : 'erhöht')}
        onBack={back}
      />
    )
  }
  if (view === 'fehler') {
    return (
      <FehlerVerhaltenPanel
        value={profile.error_behavior as ErrorBehavior}
        onChange={(value) => void updateField('error_behavior', value)}
        onBack={back}
      />
    )
  }
  if (view === 'schleifen') {
    return (
      <SchleifenerkennungPanel
        active={profile.loop_detection_enabled}
        sensitivity={profile.loop_detection_sensitivity as LoopSensitivity}
        onToggle={() => void updateField('loop_detection_enabled', !profile.loop_detection_enabled)}
        onSensitivity={(value) => void updateField('loop_detection_sensitivity', value)}
        onBack={back}
      />
    )
  }

  return (
    <div className="flex flex-col gap-5">
      <header>
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">Voreinstellungen</div>
        <h1 className="mt-2 text-[22px] font-semibold leading-tight text-white/95">KI & Verhalten</h1>
        <p className="mt-2 text-[12px] text-white/55">Steuere wie TRION arbeitet, plant und mit Fehlern umgeht.</p>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px]">
          {loading && (
            <span className="inline-flex items-center gap-1.5 text-white/40">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Lädt…
            </span>
          )}
          {savingField && !loading && (
            <span className="inline-flex items-center gap-1.5 text-white/40">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Speichert…
            </span>
          )}
          {status && !loading && !savingField && <span className="text-emerald-300/85">{status}</span>}
          {error && <span className="text-rose-300/85">{error}</span>}
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 text-white/40 transition hover:text-white/70 disabled:opacity-50"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
            Neu laden
          </button>
        </div>
      </header>

      <div className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
        <ListRow icon={<User className="h-3.5 w-3.5" />} tint="#D4537E" label="Persona"
          desc="Charakter, Sprache und Verhaltensregeln" onClick={() => setView('persona')} disabled={loading} />
        <ListRow icon={<Zap className="h-3.5 w-3.5" />} tint="#7F77DD" label="Arbeitsmodus"
          desc="Wann hält TRION vor Tool-Schritten an und wann läuft er weiter?" value={AUTONOMY_LABELS[profile.mode as AutonomyMode]} onClick={() => setView('arbeitsmodus')} disabled={loading} />
        <ListRow icon={<Layers className="h-3.5 w-3.5" />} tint="#378ADD" label="Planungstiefe"
          desc="Wie viele Schritte darf TRION vorausdenken?" value={DEPTH_LABELS[profile.planning_depth as PlanningDepth]} onClick={() => setView('planungstiefe')} disabled={loading} />
        <ListRow icon={<Clock className="h-3.5 w-3.5" />} tint="#1D9E75" label="Warteverhalten"
          desc="Weiterplanen während du tippst?" value={WAIT_LABELS[profile.wait_behavior as WaitBehavior]} onClick={() => setView('warteverhalten')} disabled={loading} />
        <ListRow icon={<Shield className="h-3.5 w-3.5" />} tint="#D4537E" label="Sicherheitsebene"
          desc="Wie konservativ behandelt TRION einfache oder unsichere Fälle?" value={askBeforeTools ? 'Erhöht' : 'Standard'} onClick={() => setView('sicherheit')} disabled={loading} />
        <ListRow icon={<RefreshCw className="h-3.5 w-3.5" />} tint="#BA7517" label="Fehlerverhalten"
          desc="Wie eskaliert TRION nach Schrittfehlern?" value={ERROR_LABELS[profile.error_behavior as ErrorBehavior]} onClick={() => setView('fehler')} disabled={loading} />
        <ListRow icon={<GitBranch className="h-3.5 w-3.5" />} tint="#6E6E73" label="Schleifenerkennung"
          desc="Endlosschleifen automatisch unterbrechen" value={profile.loop_detection_enabled ? 'Aktiv' : 'Inaktiv'} onClick={() => setView('schleifen')} disabled={loading} />
        <ListRow icon={<Brain className="h-3.5 w-3.5" />} tint="#9C7BD4" label="Erinnerung"
          desc="Darf TRION sich Dinge merken? Standard fuer neue Unterhaltungen." value={memoryLabel(memoryDefaults.memory_mode, memoryDefaults.do_not_remember)} onClick={() => setView('memory')} disabled={loading} last />
      </div>
    </div>
  )
}

interface ListRowProps {
  icon: React.ReactNode; tint: string; label: string; desc: string
  value?: string; onClick: () => void; disabled?: boolean; last?: boolean
}

function ListRow({ icon, tint, label, desc, value, onClick, disabled = false, last }: ListRowProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-white/[0.03] disabled:cursor-not-allowed disabled:opacity-60',
        !last && 'border-b border-white/5',
      )}
    >
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-white" style={{ backgroundColor: tint }}>
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[13px] text-white/88">{label}</div>
        <div className="mt-0.5 text-[11px] text-white/40">{desc}</div>
      </div>
      {value && <span className="shrink-0 text-[11px] text-white/35">{value}</span>}
      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-white/25" />
    </button>
  )
}
