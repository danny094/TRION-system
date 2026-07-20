import { useState, useEffect } from 'react'

const DAYS   = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']
const MONTHS = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']

function snapshot() {
  const d = new Date()
  return {
    time: `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`,
    date: `${DAYS[d.getDay()]}, ${d.getDate()}. ${MONTHS[d.getMonth()]}`,
  }
}

export function DesktopClock() {
  const [display, setDisplay] = useState(snapshot)

  useEffect(() => {
    const id = setInterval(() => setDisplay(snapshot()), 10_000)
    return () => clearInterval(id)
  }, [])

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
