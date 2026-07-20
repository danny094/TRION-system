import type { PersonaDraft } from '@/features/settings/personaEditor'
import { listToText, textToList } from '@/features/settings/personaEditor'

interface TextField {
  label: string
  value: string
  onChange: (value: string) => void
}

export function PersonaEditorBody({
  draft,
  content,
  onChange,
}: {
  draft: PersonaDraft
  content: string
  onChange: (draft: PersonaDraft) => void
}) {
  return (
    <div className="mt-4 grid gap-4 2xl:grid-cols-2">
      <TextCard title="Identität" fields={[
        field('Name', draft.identity.name, (v) => onChange({ ...draft, identity: { ...draft.identity, name: v } })),
        field('Rolle', draft.identity.role, (v) => onChange({ ...draft, identity: { ...draft.identity, role: v } })),
        field('Sprache', draft.identity.language, (v) => onChange({ ...draft, identity: { ...draft.identity, language: v } })),
        field('User-Name', draft.identity.userName, (v) => onChange({ ...draft, identity: { ...draft.identity, userName: v } })),
      ]} />
      <TextCard title="Stil" fields={[
        field('Tone', draft.style.tone, (v) => onChange({ ...draft, style: { ...draft.style, tone: v } })),
        field('Verbosity', draft.style.verbosity, (v) => onChange({ ...draft, style: { ...draft.style, verbosity: v } })),
        field('Format', draft.style.format, (v) => onChange({ ...draft, style: { ...draft.style, format: v } })),
      ]} />
      <ListCard title="Persönlichkeit" value={listToText(draft.lists.personality)} onChange={(v) => onChange({ ...draft, lists: { ...draft.lists, personality: textToList(v) } })} />
      <ListCard title="Core Philosophy" value={listToText(draft.lists.corePhilosophy)} onChange={(v) => onChange({ ...draft, lists: { ...draft.lists, corePhilosophy: textToList(v) } })} />
      <ListCard title="Regeln" value={listToText(draft.lists.rules)} onChange={(v) => onChange({ ...draft, lists: { ...draft.lists, rules: textToList(v) } })} />
      <ListCard title="Privacy" value={listToText(draft.lists.privacy)} onChange={(v) => onChange({ ...draft, lists: { ...draft.lists, privacy: textToList(v) } })} />
      <TextCard title="Greetings" fields={[
        field('Neuer User', draft.greetings.newUser, (v) => onChange({ ...draft, greetings: { ...draft.greetings, newUser: v } })),
        field('Bekannter User', draft.greetings.knownUser, (v) => onChange({ ...draft, greetings: { ...draft.greetings, knownUser: v } })),
        field('Farewell', draft.greetings.farewell, (v) => onChange({ ...draft, greetings: { ...draft.greetings, farewell: v } })),
      ]} />
      <div className="rounded-2xl border border-white/6 bg-white/[0.015] p-4 2xl:col-span-2">
        <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-white/35">Generierte Persona-Datei</div>
        <pre className="mt-3 overflow-x-auto rounded-2xl border border-white/8 bg-black/30 px-4 py-3 text-[11px] leading-5 text-white/72">{content}</pre>
      </div>
    </div>
  )
}

export function Banner({ kind, children }: { kind: 'error' | 'success'; children: React.ReactNode }) {
  const cls = kind === 'error' ? 'border-rose-500/20 bg-rose-500/[0.06] text-rose-200' : 'border-emerald-500/20 bg-emerald-500/[0.06] text-emerald-200'
  return <div className={`rounded-2xl border px-4 py-2.5 text-[12px] ${cls}`}>{children}</div>
}

function TextCard({ title, fields }: { title: string; fields: TextField[] }) {
  return (
    <div className="rounded-2xl border border-white/6 bg-white/[0.015] p-4">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-white/35">{title}</div>
      <div className="mt-3 space-y-3">
        {fields.map((item) => (
          <label key={item.label} className="block">
            <div className="mb-1.5 text-[11px] text-white/45">{item.label}</div>
            <input value={item.value} onChange={(e) => item.onChange(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[12px] text-white/90 outline-none transition focus:border-white/20" />
          </label>
        ))}
      </div>
    </div>
  )
}

function ListCard({ title, value, onChange }: { title: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="rounded-2xl border border-white/6 bg-white/[0.015] p-4">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-white/35">{title}</div>
      <p className="mt-1 text-[10px] text-white/30">Ein Eintrag pro Zeile.</p>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} spellCheck={false}
        className="mt-3 min-h-[120px] w-full rounded-2xl border border-white/10 bg-black/20 px-3 py-2.5 text-[11px] leading-5 text-white/88 outline-none transition focus:border-white/20" />
    </div>
  )
}

function field(label: string, value: string, onChange: (value: string) => void): TextField {
  return { label, value, onChange }
}
