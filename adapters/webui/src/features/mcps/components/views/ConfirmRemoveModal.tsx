import { AlertTriangle, X } from 'lucide-react'

interface ConfirmRemoveModalProps {
  title: string
  subtitle: string
  onCancel: () => void
  onConfirm: () => void
}

export function ConfirmRemoveModal({ title, subtitle, onCancel, onConfirm }: ConfirmRemoveModalProps) {
  return (
    <div
      className="fixed inset-0 z-[110] flex items-center justify-center bg-black/55 backdrop-blur-sm"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-sm rounded-3xl border border-rose-500/25 bg-[#16100f] p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-500/15 text-rose-300">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-semibold text-white/95">{title}</div>
              <div className="text-xs text-white/50">{subtitle}</div>
            </div>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg p-1 text-white/45 transition hover:bg-white/5 hover:text-white/85"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-4 text-xs leading-relaxed text-white/60">
          Files and configuration will be deleted. This action cannot be undone.
        </p>
        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-xl px-4 py-2 text-xs text-white/65 transition hover:bg-white/5 hover:text-white/90"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-xl border border-rose-500/30 bg-rose-500/15 px-4 py-2 text-xs font-medium text-rose-200 transition hover:bg-rose-500/25"
          >
            Remove
          </button>
        </div>
      </div>
    </div>
  )
}
