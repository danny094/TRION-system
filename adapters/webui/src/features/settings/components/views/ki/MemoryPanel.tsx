import { useState } from 'react'
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useMemoryDefaults } from '@/features/settings/useMemoryDefaults'
import type { MemoryMode } from '@/features/settings/memoryDefaultsApi'
import { DetailHeader } from './DetailHeader'

interface MemoryPanelProps {
  onBack: () => void
}

interface RadioOption {
  id: MemoryMode
  do_not_remember: boolean
  label: string
  desc: string
  isDefault?: boolean
  tint: string
}

const OPTIONS: RadioOption[] = [
  {
    id: 'global_enabled',
    do_not_remember: false,
    label: 'Ja, dauerhaft',
    desc: 'TRION lernt ueber Unterhaltungen hinweg.',
    isDefault: true,
    tint: 'border-emerald-400/40 bg-emerald-500/[0.07]',
  },
  {
    id: 'conversation_only',
    do_not_remember: false,
    label: 'Nur diese Unterhaltung',
    desc: 'Erinnerungen bleiben im aktuellen Chat, nichts geht ins Langzeitgedaechtnis.',
    tint: 'border-sky-400/40 bg-sky-500/[0.07]',
  },
  {
    id: 'disabled',
    do_not_remember: true,
    label: 'Nein, nichts',
    desc: 'Keine Speicherung, alles fluechtig.',
    tint: 'border-rose-400/40 bg-rose-500/[0.07]',
  },
]

export function MemoryPanel({ onBack }: MemoryPanelProps) {
  const { defaults, derived, loading, savingField, error, status, applyUpdate } = useMemoryDefaults()
  const [advancedOpen, setAdvancedOpen] = useState(false)

  function matches(option: RadioOption) {
    return defaults.memory_mode === option.id && defaults.do_not_remember === option.do_not_remember
  }

  function chooseOption(option: RadioOption) {
    void applyUpdate({ memory_mode: option.id, do_not_remember: option.do_not_remember })
  }

  return (
    <div className="flex flex-col gap-5">
      <DetailHeader
        title="Erinnerung"
        subtitle="Wie geht TRION mit dem um, was du teilst? Diese Einstellung gilt als Standard fuer neue Unterhaltungen."
        onBack={onBack}
      />

      <section className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
        <div className="border-b border-white/5 px-5 py-3 text-[11px] uppercase tracking-[0.18em] text-white/45">
          Darf TRION sich Dinge merken?
        </div>
        <div className="flex flex-col gap-2 p-3">
          {OPTIONS.map((option) => {
            const selected = matches(option)
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => chooseOption(option)}
                disabled={loading || !!savingField}
                className={cn(
                  'flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition disabled:opacity-60',
                  selected ? option.tint : 'border-white/8 bg-white/[0.015] hover:bg-white/[0.03]',
                )}
              >
                <div
                  className={cn(
                    'mt-0.5 h-3.5 w-3.5 shrink-0 rounded-full border-2 transition',
                    selected ? 'border-white bg-white' : 'border-white/30 bg-transparent',
                  )}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[13px] font-medium text-white/90">{option.label}</span>
                    {option.isDefault ? (
                      <span className="rounded-full bg-white/8 px-2 py-0.5 text-[9px] uppercase tracking-[0.14em] text-white/55">
                        Standard
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-1 text-[11px] leading-relaxed text-white/50">{option.desc}</div>
                </div>
              </button>
            )
          })}
        </div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
        <button
          type="button"
          onClick={() => setAdvancedOpen((open) => !open)}
          className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left text-[11px] uppercase tracking-[0.18em] text-white/45 hover:text-white/65"
        >
          <span>Erweitert</span>
          {advancedOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </button>
        {advancedOpen ? (
          <div className="border-t border-white/5 px-5 py-4 space-y-5">
            <div>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-[13px] text-white/88">Anzahl Erinnerungen pro Antwort</div>
                  <div className="mt-0.5 text-[11px] text-white/45">
                    Wie viele Treffer aus dem Memory TRION pro Antwort heranzieht.
                  </div>
                </div>
                <span className="text-[13px] font-mono text-white/85">{defaults.max_memory_hits}</span>
              </div>
              <input
                type="range"
                min={1}
                max={20}
                step={1}
                value={defaults.max_memory_hits}
                onChange={(event) => void applyUpdate({ max_memory_hits: Number(event.target.value) })}
                disabled={loading || !!savingField}
                className="mt-3 w-full accent-white/85 disabled:opacity-50"
              />
            </div>

            <div className="rounded-xl border border-white/5 bg-black/15 px-4 py-3">
              <div className="text-[10px] uppercase tracking-[0.16em] text-white/40">Aktuelle Wirkung (abgeleitet)</div>
              <ul className="mt-2 space-y-1 text-[12px] text-white/72">
                <li>
                  <span className="text-white/45">Dauerhaft speichern:</span>{' '}
                  <span className={derived.allow_long_term_write ? 'text-emerald-200/90' : 'text-rose-200/90'}>
                    {derived.allow_long_term_write ? 'ja' : 'nein'}
                  </span>
                </li>
                <li>
                  <span className="text-white/45">Cross-Conversation lesen:</span>{' '}
                  <span className={derived.allow_global_memory_read ? 'text-emerald-200/90' : 'text-rose-200/90'}>
                    {derived.allow_global_memory_read ? 'ja' : 'nein'}
                  </span>
                </li>
              </ul>
              <div className="mt-2 text-[10px] text-white/35">
                Diese Werte leiten sich aus deiner Auswahl oben ab. Sie sind nicht eigenstaendig einstellbar.
              </div>
            </div>
          </div>
        ) : null}
      </section>

      <div className="flex items-center gap-3 text-[11px]">
        {loading ? (
          <span className="inline-flex items-center gap-1.5 text-white/40">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Laedt...
          </span>
        ) : null}
        {savingField && !loading ? (
          <span className="inline-flex items-center gap-1.5 text-white/40">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Speichert...
          </span>
        ) : null}
        {status && !loading && !savingField ? <span className="text-emerald-300/85">{status}</span> : null}
        {error ? <span className="text-rose-300/85">{error}</span> : null}
      </div>
    </div>
  )
}
