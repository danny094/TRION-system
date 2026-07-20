import type { PersonaDraft } from '@/features/settings/personaEditor'
import { SubViewShell, FieldCard, FieldRow, TextInput, SelectInput, type SubViewProps } from './shared'

const LANGUAGES = [
  { value: 'Deutsch (Standard)', label: 'Deutsch (Standard)' },
  { value: 'English', label: 'English' },
  { value: 'Français', label: 'Français' },
  { value: 'Español', label: 'Español' },
]

interface Props extends SubViewProps {
  draft: PersonaDraft
  onChange: (d: PersonaDraft) => void
  onNameChange: (name: string) => void
}

export function IdentitaetView({ draft, onChange, onNameChange, onBack, onSave, saving }: Props) {
  function set<K extends keyof PersonaDraft['identity']>(key: K, value: string) {
    const next = { ...draft, identity: { ...draft.identity, [key]: value } }
    onChange(next)
    if (key === 'name') onNameChange(value)
  }

  return (
    <SubViewShell title="Identität" desc="Name, Rolle und Standard-Sprache der Persona"
      onBack={onBack} onSave={onSave} saving={saving}>
      <FieldCard>
        <FieldRow label="Name der Persona">
          <TextInput value={draft.identity.name} onChange={(v) => set('name', v)}
            placeholder="z.B. TRION" />
        </FieldRow>
        <FieldRow label="Rolle (System-Definition)">
          <TextInput value={draft.identity.role} onChange={(v) => set('role', v)}
            placeholder="z.B. Adaptive AI Software Assistant & Architect" />
        </FieldRow>
        <FieldRow label="Sprachwahl" last>
          <SelectInput
            value={draft.identity.language}
            onChange={(v) => set('language', v)}
            options={LANGUAGES}
          />
        </FieldRow>
      </FieldCard>
    </SubViewShell>
  )
}
