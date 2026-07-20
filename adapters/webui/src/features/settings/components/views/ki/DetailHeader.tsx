import { ChevronLeft } from 'lucide-react'

interface DetailHeaderProps {
  title: string
  subtitle: string
  onBack: () => void
  eyebrow?: string
  action?: React.ReactNode
}

export function DetailHeader({
  title,
  subtitle,
  onBack,
  eyebrow = 'KI & Verhalten',
  action,
}: DetailHeaderProps) {
  return (
    <div className="flex flex-col gap-4">
      <button
        type="button"
        onClick={onBack}
        className="flex w-fit items-center gap-1 text-[12px] text-purple-300/80 transition hover:text-purple-200"
      >
        <ChevronLeft className="h-3.5 w-3.5" />
        {eyebrow}
      </button>
      <header className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">
            {eyebrow}
          </div>
          <h1 className="mt-2 text-[22px] font-semibold leading-tight text-white/95">
            {title}
          </h1>
          <p className="mt-2 max-w-xl text-[12px] text-white/55">{subtitle}</p>
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </header>
    </div>
  )
}
