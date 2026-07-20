import type { PersonaDraft } from '@/features/settings/personaEditor'
import { SubViewShell, FieldCard, FieldRow, TextInput, type SubViewProps } from './shared'

interface Props extends SubViewProps {
  draft: PersonaDraft
  onChange: (d: PersonaDraft) => void
}

export function StilView({ draft, onChange, onBack, onSave, saving }: Props) {
  function set<K extends keyof PersonaDraft['style']>(key: K, value: string) {
    onChange({ ...draft, style: { ...draft.style, [key]: value } })
  }

  return (
    <SubViewShell title="Stil" desc="Tonalität, Ausgabepräferenzen und Codeformate"
      onBack={onBack} onSave={onSave} saving={saving}>
      <FieldCard>
        <FieldRow label="Ton">
          <TextInput value={draft.style.tone} onChange={(v) => set('tone', v)}
            placeholder="z.B. Direkt, präzise und sachlich" />
        </FieldRow>
        <FieldRow label="Ausführlichkeit">
          <TextInput value={draft.style.verbosity} onChange={(v) => set('verbosity', v)}
            placeholder="z.B. Kompakt" />
        </FieldRow>
        <FieldRow label="Format">
          <TextInput value={draft.style.format} onChange={(v) => set('format', v)}
            placeholder="z.B. Markdown" />
        </FieldRow>
        <FieldRow label="Code-Stil">
          <TextInput value={draft.style.code} onChange={(v) => set('code', v)}
            placeholder="z.B. Kommentare auf Deutsch" />
        </FieldRow>
        <FieldRow label="Antwortlänge" last>
          <TextInput value={draft.style.responseLength} onChange={(v) => set('responseLength', v)}
            placeholder="z.B. Angemessen zur Aufgabe" />
        </FieldRow>
      </FieldCard>
    </SubViewShell>
  )
}
