import { ChevronLeft, Loader2 } from 'lucide-react'

interface Props {
  content: string
  onBack: () => void
  onSave: () => void
  saving: boolean
}

export function PersonaJsonView({ content, onBack, onSave, saving }: Props) {
  return (
    <div className="flex flex-col gap-5">
      <header>
        <button type="button" onClick={onBack}
          className="flex items-center gap-1 text-[12px] text-primary transition hover:opacity-80">
          <ChevronLeft className="h-3.5 w-3.5" /> TRION bearbeiten
        </button>
        <div className="mt-3 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-[22px] font-semibold leading-tight text-white/95">
              Generierte Persona-Datei
            </h1>
            <p className="mt-1 text-[12px] text-white/55">
              Schreibgeschütztes JSON Modell für den Exporteinsatz
            </p>
          </div>
          <button
            type="button" onClick={onSave} disabled={saving}
            className="shrink-0 rounded-xl bg-purple-600 px-4 py-2 text-[13px] font-medium text-white
                       shadow-lg transition hover:bg-purple-500 disabled:opacity-50"
          >
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Speichern'}
          </button>
        </div>
      </header>

      <div className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
        <div className="border-b border-white/[0.04] px-4 py-2.5">
          <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/30">
            JSON Repräsentation
          </span>
        </div>
        <pre className="overflow-x-auto px-4 py-4 text-[11px] leading-relaxed text-white/70 font-mono">
          {content}
        </pre>
      </div>
    </div>
  )
}
