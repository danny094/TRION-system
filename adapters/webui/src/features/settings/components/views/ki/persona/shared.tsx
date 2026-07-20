// Shared helpers for Persona sub-views
import { ChevronLeft, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SubViewProps {
  onBack: () => void
  onSave: () => void
  saving: boolean
}

export function SubViewShell({ title, desc, backLabel = 'TRION bearbeiten', onBack, onSave, saving, children }: {
  title: string; desc: string; backLabel?: string
  children: React.ReactNode
} & SubViewProps) {
  return (
    <div className="flex flex-col gap-5">
      <header>
        <button type="button" onClick={onBack}
          className="flex items-center gap-1 text-[12px] text-primary transition hover:opacity-80">
          <ChevronLeft className="h-3.5 w-3.5" /> {backLabel}
        </button>
        <div className="mt-3 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-[22px] font-semibold leading-tight text-white/95">{title}</h1>
            <p className="mt-1 text-[12px] text-white/55">{desc}</p>
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
      {children}
    </div>
  )
}

export function FieldCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
      {children}
    </div>
  )
}

export function FieldRow({ label, last, children }: {
  label: string; last?: boolean; children: React.ReactNode
}) {
  return (
    <div className={cn('flex flex-col gap-2 px-4 py-3', !last && 'border-b border-white/[0.04]')}>
      <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-white/35">{label}</div>
      {children}
    </div>
  )
}

export function TextInput({ value, onChange, placeholder }: {
  value: string; onChange: (v: string) => void; placeholder?: string
}) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2
                 text-[13px] text-white/90 placeholder:text-white/25 outline-none
                 transition focus:border-white/20"
    />
  )
}

export function SelectInput({ value, onChange, options }: {
  value: string; onChange: (v: string) => void
  options: { value: string; label: string }[]
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-xl border border-white/10 bg-[#1c1c1e] px-3 py-2
                 text-[13px] text-white/90 outline-none transition focus:border-white/20"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}
