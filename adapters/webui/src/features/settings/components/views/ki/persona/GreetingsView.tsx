import type { PersonaDraft } from '@/features/settings/personaEditor'
import { SubViewShell, FieldCard, FieldRow, TextInput, type SubViewProps } from './shared'

interface Props extends SubViewProps {
  draft: PersonaDraft
  onChange: (d: PersonaDraft) => void
}

export function GreetingsView({ draft, onChange, onBack, onSave, saving }: Props) {
  function set<K extends keyof PersonaDraft['greetings']>(key: K, value: string) {
    onChange({ ...draft, greetings: { ...draft.greetings, [key]: value } })
  }

  return (
    <SubViewShell title="Greetings" desc="Standard-Ansprache und Begrüßungsformulierungen"
      onBack={onBack} onSave={onSave} saving={saving}>
      <FieldCard>
        <FieldRow label="Neuer User">
          <TextInput value={draft.greetings.newUser} onChange={(v) => set('newUser', v)}
            placeholder="z.B. System bereit. Was bringst du heute?" />
        </FieldRow>
        <FieldRow label="Bekannter User">
          <TextInput value={draft.greetings.knownUser} onChange={(v) => set('knownUser', v)}
            placeholder="z.B. Willkommen zurück." />
        </FieldRow>
        <FieldRow label="Farewell" last>
          <TextInput value={draft.greetings.farewell} onChange={(v) => set('farewell', v)}
            placeholder="z.B. Bis bald." />
        </FieldRow>
      </FieldCard>
    </SubViewShell>
  )
}
