import { useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Loader2, Plus, UploadCloud, X } from 'lucide-react'
import { useMcpsStore } from '../state/mcpsStore'
import { useTranslation } from '@/lib/i18n'

interface AddMcpModalProps {
  onClose: () => void
}

export function AddMcpModal({ onClose }: AddMcpModalProps) {
  const uploadBundle = useMcpsStore((s) => s.uploadBundle)
  const saving = useMcpsStore((s) => s.saving)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)
  const { t } = useTranslation()

  async function handleFileChange(file: File | null) {
    if (!file) return
    setError(null)
    try {
      await uploadBundle(file)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('mcp.installFailed'))
    }
  }

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/55 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.18 }}
        className="glass w-full max-w-md overflow-hidden rounded-3xl border border-white/12 shadow-2xl"
      >
        <header className="flex items-center justify-between border-b border-white/8 bg-white/5 px-4 py-3">
          <h3 className="flex items-center gap-2 text-sm font-medium text-white/85">
            <Plus className="h-4 w-4 text-primary" />
            {t('mcp.add')}
          </h3>
          <button
            type="button"
            onClick={onClose}
            aria-label={t('common.close')}
            className="rounded-full p-1 text-white/40 transition-colors hover:bg-white/8 hover:text-white/80"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="p-5">
          <input
            ref={inputRef}
            type="file"
            accept=".zip,.tar,.tar.gz,.tgz,application/zip"
            className="hidden"
            onChange={(event) => void handleFileChange(event.target.files?.[0] ?? null)}
          />
          <UploadDropZone
            saving={saving}
            onPick={() => inputRef.current?.click()}
          />
          <p className="mt-3 text-xs text-white/40">
            {t('mcp.archiveNote')}
          </p>
          {error && (
            <div className="mt-3 rounded-2xl border border-rose-500/20 bg-rose-500/[0.06] px-3 py-2 text-xs text-rose-200">
              {error}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  )
}

interface UploadDropZoneProps {
  saving: boolean
  onPick: () => void
}

function UploadDropZone({ saving, onPick }: UploadDropZoneProps) {
  const { t } = useTranslation()
  return (
    <button
      type="button"
      onClick={onPick}
      disabled={saving}
      className="group flex h-44 w-full flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-white/10 bg-black/20 transition-colors hover:border-primary/40 hover:bg-primary/[0.04]"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/5 group-hover:bg-primary/15">
        {saving ? (
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
        ) : (
          <UploadCloud className="h-5 w-5 text-white/55 group-hover:text-primary" />
        )}
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-white/85">
          {saving ? t('mcp.installingBundle') : t('mcp.chooseArchive')}
        </p>
        <p className="mt-1 text-xs text-white/40">
          {saving ? t('mcp.wait') : t('mcp.chooseLocalFile')}
        </p>
      </div>
    </button>
  )
}
