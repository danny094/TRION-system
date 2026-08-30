import { useState, useEffect } from 'react'
import { useTranslation } from '@/lib/i18n'

function snapshot(locale: string) {
  const d = new Date()
  return {
    time: `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`,
    date: new Intl.DateTimeFormat(locale, { weekday: 'short', day: 'numeric', month: 'short' }).format(d),
  }
}

export function DesktopClock() {
  const { locale } = useTranslation()
  const [display, setDisplay] = useState(() => snapshot(locale))

  useEffect(() => {
    setDisplay(snapshot(locale))
    const id = setInterval(() => setDisplay(snapshot(locale)), 10_000)
    return () => clearInterval(id)
  }, [locale])

  return (
    <div className="fixed top-4 right-6 z-50 flex flex-col items-end gap-0.5 pointer-events-none select-none">
      <span className="text-xl font-semibold text-white/80 tabular-nums leading-none">
        {display.time}
      </span>
      <span className="text-[11px] text-white/35 leading-none">
        {display.date}
      </span>
    </div>
  )
}
