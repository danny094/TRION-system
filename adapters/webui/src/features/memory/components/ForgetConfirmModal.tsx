import { AlertTriangle } from 'lucide-react'

interface ForgetConfirmModalProps {
  open: boolean
  title?: string
  description: string
  onConfirm: () => void
  onCancel: () => void
  busy?: boolean
}

export function ForgetConfirmModal({
  open,
  title = 'Erinnerung vergessen?',
  description,
  onConfirm,
  onCancel,
  busy = false,
}: ForgetConfirmModalProps) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onCancel}>
      <div
        className="w-[400px] rounded-2xl border border-white/10 bg-[#1a1a1d] shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start gap-3 px-5 pt-5">
          <div className="rounded-xl border border-rose-400/25 bg-rose-500/10 p-2 text-rose-200/90">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div className="flex-1">
            <div className="text-[14px] font-semibold text-white/88">{title}</div>
            <div className="mt-1 text-[12px] leading-relaxed text-white/65">{description}</div>
            <div className="mt-2 text-[11px] uppercase tracking-[0.16em] text-white/35">
              Kann nicht rueckgaengig gemacht werden.
            </div>
          </div>
        </div>
        <div className="mt-5 flex items-center justify-end gap-2 border-t border-white/5 px-5 py-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-[12px] text-white/75 hover:bg-white/10 disabled:opacity-40"
          >
            Abbrechen
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className="rounded-lg border border-rose-400/30 bg-rose-500/20 px-3 py-1.5 text-[12px] font-medium text-rose-100 hover:bg-rose-500/30 disabled:opacity-40"
          >
            {busy ? 'Vergesse...' : 'Vergessen'}
          </button>
        </div>
      </div>
    </div>
  )
}
