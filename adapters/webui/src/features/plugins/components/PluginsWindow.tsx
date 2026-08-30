import { useEffect, useRef } from 'react'
import { Loader2, Trash2, Upload } from 'lucide-react'
import { usePluginStore } from '@/features/plugins/state/pluginStore'
import { useTranslation } from '@/lib/i18n'

export function PluginsWindow() {
  const fileRef = useRef<HTMLInputElement>(null)
  const { items, loading, refresh, upload, toggle, remove } = usePluginStore()
  const { t } = useTranslation()
  useEffect(() => { if (items.length === 0) void refresh() }, [items.length, refresh])

  return (
    <div className="flex h-full flex-col gap-4 p-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">{t('plugins.installer')}</div>
          <h1 className="mt-2 text-[22px] font-semibold text-white/95">Plugins</h1>
          <p className="mt-2 max-w-xl text-[12px] text-white/55">{t('plugins.description')}</p>
        </div>
        <button type="button" onClick={() => fileRef.current?.click()} className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] text-white/80 transition hover:bg-white/[0.08]"><Upload className="h-3.5 w-3.5" />{t('plugins.install')}</button>
      </header>
      <input ref={fileRef} type="file" accept=".zip,.tar,.tar.gz,.tgz" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload(file); event.target.value = '' }} />
      <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        {loading ? <div className="flex items-center justify-center py-16 text-[12px] text-white/35"><Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />{t('plugins.loading')}</div> : (
          <div className="space-y-3">
            {items.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-4 rounded-2xl border border-white/8 bg-white/[0.02] px-4 py-3">
                <div className="min-w-0">
                  <div className="text-[13px] font-medium text-white/90">{item.name}</div>
                  <div className="mt-1 text-[11px] text-white/40">{item.id} · {item.kind} · {item.mount} · v{item.version}</div>
                  <div className="mt-1 text-[11px] text-white/55">{item.description || t('plugins.noDescription')}</div>
                  {item.missingMcp.length > 0 ? <div className="mt-1 text-[11px] text-amber-300/80">{t('plugins.missingMcps', { names: item.missingMcp.join(', ') })}</div> : null}
                </div>
                <div className="flex items-center gap-2">
                  <button type="button" onClick={() => void toggle(item.id, !item.enabled)} className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] text-white/80 transition hover:bg-white/[0.08]">{item.enabled ? t('plugins.disable') : t('plugins.enable')}</button>
                  <button type="button" onClick={() => void remove(item.id)} aria-label={t('plugins.remove', { name: item.name })} className="flex h-8 w-8 items-center justify-center rounded-lg border border-rose-500/20 bg-rose-500/[0.08] text-rose-200 transition hover:bg-rose-500/[0.14]"><Trash2 className="h-3.5 w-3.5" /></button>
                </div>
              </div>
            ))}
            {items.length === 0 ? <div className="py-16 text-center text-[12px] text-white/30">{t('plugins.none')}</div> : null}
          </div>
        )}
      </section>
    </div>
  )
}
