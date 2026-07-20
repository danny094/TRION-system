import { useEffect, useState, useMemo } from 'react'
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { fetchPersona, updatePersona } from '@/features/settings/personaApi'
import {
  buildPersonaContent, createEmptyPersonaDraft, parsePersonaContent,
  type PersonaDraft,
} from '@/features/settings/personaEditor'
import { IdentitaetView }     from './persona/IdentitaetView'
import { StilView }           from './persona/StilView'
import { ListenView }         from './persona/ListenView'
import { GreetingsView }      from './persona/GreetingsView'
import { PersonaJsonView }    from './persona/PersonaJsonView'

type SubScreen =
  | { kind: 'list' }
  | { kind: 'identitaet' }
  | { kind: 'stil' }
  | { kind: 'persoenlichkeit' }
  | { kind: 'philosophie' }
  | { kind: 'regeln' }
  | { kind: 'privacy' }
  | { kind: 'greetings' }
  | { kind: 'json' }

interface Section {
  id: SubScreen['kind']
  emoji: string
  tint: string
  label: string
  desc: string
  preview: (d: PersonaDraft) => string
}

const SECTIONS: Section[] = [
  { id: 'identitaet',    emoji: '👤', tint: '#5B6AF8', label: 'Identität',        desc: 'Name, Rolle und Standard-Sprache der Persona',       preview: (d) => [d.identity.name, d.identity.role].filter(Boolean).join(', ') },
  { id: 'stil',          emoji: '🎨', tint: '#E0812A', label: 'Stil',              desc: 'Tonalität, Ausgabepräferenzen und Codeformate',       preview: (d) => [d.style.tone, d.style.verbosity].filter(Boolean).join(', ') },
  { id: 'persoenlichkeit', emoji: '🦊', tint: '#D4537E', label: 'Persönlichkeit', desc: 'Charakter-Eigenschaften, Empathie und Humorlevel',    preview: (d) => d.lists.personality.slice(0, 3).join(', ') },
  { id: 'philosophie',   emoji: '🌿', tint: '#2D9E7A', label: 'Core-Philosophie', desc: 'Grundhaltung zur Problemlösung und Interaktion',      preview: (d) => d.lists.corePhilosophy[0] ?? '' },
  { id: 'regeln',        emoji: '⚖️', tint: '#9B6E3E', label: 'Regeln',           desc: 'System-Instruktionen und harte Logik-Leitplanken',   preview: (d) => `${d.lists.rules.length} Regel-Element${d.lists.rules.length !== 1 ? 'e' : ''}` },
  { id: 'privacy',       emoji: '🔒', tint: '#4A7D9B', label: 'Privacy',          desc: 'Lokale Speicherung und Daten-Sperrfristen',           preview: (d) => d.lists.privacy[0] ?? '' },
  { id: 'greetings',     emoji: '👋', tint: '#7B6EAB', label: 'Greetings',        desc: 'Standard-Ansprache und Begrüßungsformulierungen',     preview: (d) => d.greetings.newUser.slice(0, 30) || '' },
  { id: 'json',          emoji: '📄', tint: '#4B5563', label: 'Generierte Datei', desc: 'Schreibgeschütztes JSON Modell für den Exporteinsatz', preview: () => 'JSON anzeigen' },
]

interface Props {
  personaName: string
  isNew: boolean
  isActive: boolean
  onBack: () => void
}

export function PersonaEditorView({ personaName, isNew, isActive, onBack }: Props) {
  const [sub, setSub]     = useState<SubScreen>({ kind: 'list' })
  const [draft, setDraft] = useState<PersonaDraft>(createEmptyPersonaDraft())
  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving]   = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [status, setStatus]   = useState<string | null>(null)
  const [name, setName]       = useState(personaName)

  const content = useMemo(() => buildPersonaContent(draft), [draft])

  useEffect(() => {
    if (!isNew && personaName) void loadData(personaName)
  }, [personaName, isNew])

  async function loadData(n: string) {
    setLoading(true); setError(null)
    try { const p = await fetchPersona(n); setDraft(parsePersonaContent(p.content)) }
    catch (err) { setError(msg(err)) }
    finally { setLoading(false) }
  }

  async function save() {
    const n = name.trim()
    if (!n) { setError('Bitte zuerst einen Namen in Identität eingeben.'); return }
    setSaving(true); setError(null); setStatus(null)
    try {
      await updatePersona(n, content)
      setStatus('Persona gespeichert.')
    } catch (err) { setError(msg(err)) }
    finally { setSaving(false) }
  }

  const displayName = name || (isNew ? 'Neue Persona' : personaName)

  // ── Sub-screen routing ────────────────────────────────────────────────────
  if (sub.kind === 'identitaet') return (
    <IdentitaetView draft={draft} onChange={setDraft} onBack={() => setSub({ kind: 'list' })}
      onSave={() => void save()} saving={saving} onNameChange={setName} />
  )
  if (sub.kind === 'stil') return (
    <StilView draft={draft} onChange={setDraft} onBack={() => setSub({ kind: 'list' })}
      onSave={() => void save()} saving={saving} />
  )
  if (sub.kind === 'persoenlichkeit') return (
    <ListenView title="Persönlichkeit" desc="Charakter-Eigenschaften, Empathie und Humorlevel"
      items={draft.lists.personality}
      onChange={(v) => setDraft({ ...draft, lists: { ...draft.lists, personality: v } })}
      onBack={() => setSub({ kind: 'list' })} onSave={() => void save()} saving={saving} />
  )
  if (sub.kind === 'philosophie') return (
    <ListenView title="Core-Philosophie" desc="Grundhaltung zur Problemlösung und Interaktion"
      items={draft.lists.corePhilosophy}
      onChange={(v) => setDraft({ ...draft, lists: { ...draft.lists, corePhilosophy: v } })}
      onBack={() => setSub({ kind: 'list' })} onSave={() => void save()} saving={saving} />
  )
  if (sub.kind === 'regeln') return (
    <ListenView title="Regeln" desc="System-Instruktionen und harte Logik-Leitplanken"
      items={draft.lists.rules}
      onChange={(v) => setDraft({ ...draft, lists: { ...draft.lists, rules: v } })}
      onBack={() => setSub({ kind: 'list' })} onSave={() => void save()} saving={saving} numbered />
  )
  if (sub.kind === 'privacy') return (
    <ListenView title="Privacy" desc="Lokale Speicherung und Daten-Sperrfristen"
      items={draft.lists.privacy}
      onChange={(v) => setDraft({ ...draft, lists: { ...draft.lists, privacy: v } })}
      onBack={() => setSub({ kind: 'list' })} onSave={() => void save()} saving={saving} />
  )
  if (sub.kind === 'greetings') return (
    <GreetingsView draft={draft} onChange={setDraft} onBack={() => setSub({ kind: 'list' })}
      onSave={() => void save()} saving={saving} />
  )
  if (sub.kind === 'json') return (
    <PersonaJsonView content={content} onBack={() => setSub({ kind: 'list' })}
      onSave={() => void save()} saving={saving} />
  )

  // ── Ebene 2: Drill-Down Liste ─────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-5">
      <header>
        <button type="button" onClick={onBack}
          className="flex items-center gap-1 text-[12px] text-primary transition hover:opacity-80">
          <ChevronLeft className="h-3.5 w-3.5" /> KI & Verhalten
        </button>
        <div className="mt-3 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-[22px] font-semibold leading-tight text-white/95">
              {displayName} bearbeiten
            </h1>
            <p className="mt-1 text-[12px] text-white/55">
              Konfiguriere Charakter-Inlays für {displayName} (Aufgeteilt in Teilbereiche)
            </p>
          </div>
          <button
            type="button"
            onClick={() => void save()}
            disabled={saving}
            className="shrink-0 rounded-xl bg-purple-600 px-4 py-2 text-[13px] font-medium text-white
                       shadow-lg transition hover:bg-purple-500 disabled:opacity-50"
          >
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Speichern'}
          </button>
        </div>
        {isActive && (
          <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-primary/15 px-2.5 py-1 text-[11px] text-primary">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            Aktive Persona
          </div>
        )}
      </header>

      {error && <Banner kind="error">{error}</Banner>}
      {status && !error && <Banner kind="success">{status}</Banner>}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-[12px] text-white/35">
          <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> Persona wird geladen
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
          {SECTIONS.map((sec, idx) => (
            <EditorRow
              key={sec.id}
              section={sec}
              preview={sec.preview(draft)}
              last={idx === SECTIONS.length - 1}
              onClick={() => setSub({ kind: sec.id as SubScreen['kind'] })}
            />
          ))}
        </div>
      )}
    </div>
  )
}

/* ── EditorRow ──────────────────────────────────────────────────────────────── */

function EditorRow({ section, preview, last, onClick }: {
  section: Section; preview: string; last: boolean; onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-3 px-4 py-3.5 text-left transition hover:bg-white/[0.03]',
        !last && 'border-b border-white/[0.04]',
      )}
    >
      <div
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-[16px]"
        style={{ backgroundColor: section.tint + '33' }}
      >
        {section.emoji}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[13px] font-medium text-white/88">{section.label}</div>
        <div className="mt-0.5 text-[11px] text-white/40">{section.desc}</div>
      </div>
      {preview && (
        <span className="max-w-[140px] truncate text-right text-[11px] text-white/35 shrink-0">
          {preview}
        </span>
      )}
      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-white/25" />
    </button>
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
