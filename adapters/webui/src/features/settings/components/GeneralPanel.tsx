import { useUiStore } from '@/state/uiStore'
import { useTranslation } from '@/lib/i18n'

export function GeneralPanel() {
  const { dockAutoHide, locale, setDockAutoHide, setLocale } = useUiStore()
  const { t } = useTranslation()

  return (
    <div className="flex flex-col gap-5">
      <header>
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">
          {t('general.preferences')}
        </div>
        <h1 className="mt-2 text-[22px] font-semibold leading-tight text-white/95">
          {t('general.title')}
        </h1>
        <p className="mt-2 text-[12px] text-white/55">
          {t('general.description')}
        </p>
      </header>

      <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-white/50">
          {t('general.dock')}
        </div>
        <div className="mt-3 flex items-center justify-between">
          <div>
            <div className="text-[13px] text-white/80">{t('general.hideDock')}</div>
            <div className="mt-0.5 text-[11px] text-white/35">
              {t('general.hideDockHint')}
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={dockAutoHide}
            aria-label={t('general.hideDock')}
            onClick={() => setDockAutoHide(!dockAutoHide)}
            className={[
              'relative h-6 w-10 shrink-0 rounded-full transition-colors duration-200',
              dockAutoHide ? 'bg-white/30' : 'bg-white/10',
            ].join(' ')}
          >
            <span
              className={[
                'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform duration-200',
                dockAutoHide ? 'translate-x-4' : 'translate-x-0.5',
              ].join(' ')}
            />
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-white/50">
          {t('general.language')}
        </div>
        <div className="mt-3 flex items-center justify-between gap-4">
          <div className="text-[11px] text-white/35">{t('general.languageHint')}</div>
          <select
            value={locale}
            aria-label={t('general.language')}
            onChange={(event) => setLocale(event.target.value as typeof locale)}
            className="rounded-lg border border-white/10 bg-white/[0.05] px-2.5 py-1.5 text-xs text-white/80 outline-none"
          >
            <option value="en">{t('language.english')}</option>
            <option value="de">{t('language.german')}</option>
          </select>
        </div>
      </section>
    </div>
  )
}
