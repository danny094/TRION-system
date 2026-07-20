import { useEffect, useState, useRef } from 'react'
import { ChevronLeft, ChevronRight, ChevronDown, Loader2, Plus, Pencil } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  fetchPersonas, switchPersona,
} from '@/features/settings/personaApi'
import { PersonaEditorView } from './PersonaEditorView'

type Screen =
  | { kind: 'list' }
  | { kind: 'editor'; personaName: string; isNew: boolean }

interface Props { onBack: () => void }

export function PersonaPanel({ onBack }: Props) {
  const [screen, setScreen]   = useState<Screen>({ kind: 'list' })
  const [personas, setPersonas] = useState<string[]>([])
  const [active, setActive]   = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  useEffect(() => { void loadAll() }, [])

  async function loadAll() {
    setLoading(true); setError(null)
    try {
      const p = await fetchPersonas()
      setPersonas(p.personas)
      setActive(p.active)
    } catch (err) { setError(msg(err)) }
    finally { setLoading(false) }
  }

  async function handleSwitch(name: string) {
    try { await switchPersona(name); setActive(name) }
    catch (err) { setError(msg(err)) }
  }

  if (screen.kind === 'editor') {
    return (
      <PersonaEditorView
        personaName={screen.personaName}
        isNew={screen.isNew}
        isActive={screen.personaName === active}
        onBack={() => { setScreen({ kind: 'list' }); void loadAll() }}
      />
    )
  }

  return (
    <div className="flex flex-col gap-5">
      <header>
        <button type="button" onClick={onBack}
          className="flex items-center gap-1 text-[12px] text-primary transition hover:opacity-80">
          <ChevronLeft className="h-3.5 w-3.5" /> KI & Verhalten
        </button>
        <h1 className="mt-3 text-[22px] font-semibold leading-tight text-white/95">KI & Verhalten</h1>
        <p className="mt-1 text-[12px] text-white/55">Steuere wie TRION arbeitet, plant und mit Fehlern umgeht.</p>
      </header>

      {error && <Banner kind="error">{error}</Banner>}

      {/* Aktive Persona */}
      <div className="flex flex-col gap-1">
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35 px-1">
          Aktive Persona
        </div>
        <div className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
          <PersonaSwitcher
            personas={personas}
            active={active}
            loading={loading}
            onSwitch={handleSwitch}
          />
        </div>
      </div>

      {/* Personas bearbeiten */}
      <div className="flex flex-col gap-1">
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35 px-1">
          Existierende Personas bearbeiten
        </div>
        <div className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
          {loading ? (
            <div className="flex items-center gap-2 px-4 py-4 text-[12px] text-white/35">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Lädt…
            </div>
          ) : personas.length === 0 ? (
            <div className="px-4 py-4 text-[12px] text-white/30">Keine Personas gefunden.</div>
          ) : (
            personas.map((name, idx) => (
              <PersonaRow
                key={name}
                name={name}
                isActive={name === active}
                last={idx === personas.length - 1}
                onEdit={() => setScreen({ kind: 'editor', personaName: name, isNew: false })}
              />
            ))
          )}
        </div>
      </div>

      {/* Neue Persona */}
      <button
        type="button"
        onClick={() => setScreen({ kind: 'editor', personaName: '', isNew: true })}
        className="flex items-center gap-2 rounded-2xl border border-white/8 bg-white/[0.02]
                   px-4 py-3 text-[13px] text-white/60 transition hover:bg-white/[0.04] hover:text-white/85"
      >
        <Plus className="h-4 w-4" />
        Neue Persona erstellen
      </button>
    </div>
  )
}

/* ── PersonaSwitcher (Dropdown-Row) ────────────────────────────────────────── */

function PersonaSwitcher({ personas, active, loading, onSwitch }: {
  personas: string[]; active: string; loading: boolean; onSwitch: (name: string) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onOutside)
    return () => document.removeEventListener('mousedown', onOutside)
  }, [])

  const initial = active ? active[0].toUpperCase() : '?'

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={loading}
        className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition hover:bg-white/[0.03]"
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-purple-600/80 text-[13px] font-bold text-white">
          {initial}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-medium text-white/85">Persona wechseln</div>
          <div className="mt-0.5 text-[11px] text-white/40">{active} (Standard-Persona aktiv)</div>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[12px] font-medium text-primary">{active}</span>
          <ChevronDown className={cn('h-3.5 w-3.5 text-primary transition-transform', open && 'rotate-180')} />
        </div>
      </button>

      {open && (
        <div className="absolute right-2 top-full z-50 mt-1 min-w-[160px] overflow-hidden rounded-xl
                        border border-white/10 bg-[#1c1c1e] shadow-2xl">
          {personas.map((name) => (
            <button
              key={name}
              type="button"
              onClick={() => { onSwitch(name); setOpen(false) }}
              className={cn(
                'flex w-full items-center gap-2 px-4 py-2.5 text-left text-[13px] transition hover:bg-white/[0.06]',
                name === active ? 'text-primary' : 'text-white/80',
              )}
            >
              {name === active && <span className="h-1.5 w-1.5 rounded-full bg-primary" />}
              {name !== active && <span className="h-1.5 w-1.5" />}
              {name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

/* ── PersonaRow ─────────────────────────────────────────────────────────────── */

function PersonaRow({ name, isActive, last, onEdit }: {
  name: string; isActive: boolean; last: boolean; onEdit: () => void
}) {
  const initial = name[0]?.toUpperCase() ?? '?'
  const tints = ['#7C3AED', '#2563EB', '#059669', '#DC2626', '#D97706', '#0891B2']
  const tint = tints[name.charCodeAt(0) % tints.length]

  return (
    <div className={cn('flex items-center gap-3 px-4 py-3', !last && 'border-b border-white/[0.04]')}>
      <div
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-[13px] font-bold text-white"
        style={{ backgroundColor: tint }}
      >
        {initial}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-medium text-white/85">{name}</span>
          {isActive && (
            <span className="rounded-full bg-primary/20 px-2 py-0.5 text-[10px] font-medium text-primary">
              Aktiv
            </span>
          )}
        </div>
        <div className="mt-0.5 text-[11px] text-white/35">Bearbeite Identität, Stil, Regeln & Verhalten</div>
      </div>
      <button
        type="button"
        onClick={onEdit}
        className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.04]
                   px-3 py-1.5 text-[11px] text-white/60 transition hover:bg-white/[0.08] hover:text-white/90"
      >
        <Pencil className="h-3 w-3" />
        Bearbeiten
      </button>
      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-white/20" />
    </div>
  )
}

function msg(err: unknown): string {
  return err instanceof Error ? err.message : 'Unbekannter Fehler'
}

function Banner({ kind, children }: { kind: 'error' | 'success'; children: React.ReactNode }) {
  const cls = kind === 'error'
    ? 'border-rose-500/20 bg-rose-500/[0.06] text-rose-200'
    : 'border-emerald-500/20 bg-emerald-500/[0.06] text-emerald-200'
  return <div className={cn('rounded-2xl border px-4 py-2.5 text-[12px]', cls)}>{children}</div>
}
