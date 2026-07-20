import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { SubViewShell, FieldCard, type SubViewProps } from './shared'

interface Props extends SubViewProps {
  title: string
  desc: string
  items: string[]
  onChange: (items: string[]) => void
  numbered?: boolean
}

export function ListenView({ title, desc, items, onChange, numbered = false, onBack, onSave, saving }: Props) {
  const [input, setInput] = useState('')

  function add() {
    const trimmed = input.trim()
    if (!trimmed) return
    onChange([...items, trimmed])
    setInput('')
  }

  function remove(idx: number) {
    onChange(items.filter((_, i) => i !== idx))
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); add() }
  }

  return (
    <SubViewShell title={title} desc={desc} onBack={onBack} onSave={onSave} saving={saving}>
      <FieldCard>
        {items.length === 0 ? (
          <div className="px-4 py-6 text-center text-[12px] text-white/25">
            Noch keine Einträge. Füge den ersten hinzu.
          </div>
        ) : (
          items.map((item, idx) => (
            <div
              key={idx}
              className={cn(
                'flex items-start gap-3 px-4 py-3',
                idx < items.length - 1 && 'border-b border-white/[0.04]',
              )}
            >
              <span className="mt-0.5 shrink-0 text-[11px] text-white/30 w-5 text-right">
                {numbered ? `${idx + 1}.` : '—'}
              </span>
              <span className="flex-1 text-[13px] text-white/80 leading-relaxed">{item}</span>
              <button
                type="button"
                onClick={() => remove(idx)}
                className="mt-0.5 shrink-0 text-white/20 transition hover:text-rose-400"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))
        )}
      </FieldCard>

      {/* Add input */}
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder={`Neuen Eintrag hinzufügen…`}
          className="flex-1 rounded-xl border border-white/10 bg-white/[0.02] px-3 py-2.5
                     text-[13px] text-white/90 placeholder:text-white/25 outline-none
                     transition focus:border-white/20"
        />
        <button
          type="button"
          onClick={add}
          className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.04]
                     px-3 py-2.5 text-[12px] text-white/60 transition hover:bg-white/[0.08] hover:text-white/90"
        >
          <Plus className="h-3.5 w-3.5" />
          Hinzufügen
        </button>
      </div>
    </SubViewShell>
  )
}
