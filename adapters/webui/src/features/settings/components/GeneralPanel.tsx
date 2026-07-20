import { useUiStore } from '@/state/uiStore'

export function GeneralPanel() {
  const { dockAutoHide, setDockAutoHide } = useUiStore()

  return (
    <div className="flex flex-col gap-5">
      <header>
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">
          Voreinstellungen
        </div>
        <h1 className="mt-2 text-[22px] font-semibold leading-tight text-white/95">
          Allgemein
        </h1>
        <p className="mt-2 text-[12px] text-white/55">
          Grundlegende Einstellungen der Oberfläche.
        </p>
      </header>

      <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-4">
        <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-white/50">
          Dock
        </div>
        <div className="mt-3 flex items-center justify-between">
          <div>
            <div className="text-[13px] text-white/80">Dock automatisch ausblenden</div>
            <div className="mt-0.5 text-[11px] text-white/35">
              Dock einblenden, wenn der Mauszeiger unten andockt.
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={dockAutoHide}
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
    </div>
  )
}
