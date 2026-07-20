/**
 * ProgressUtteranceList — rendert deterministisch erzeugte Fortschrittszeilen.
 *
 * Liest ausschließlich aus msg.events (progress_utterance-Events).
 * Berührt msg.content nicht.
 * Invariante: text enthält niemals Tool-Ergebnisinhalte.
 */
import type { ChatEvent, ProgressUtteranceEvent } from '@/lib/contracts/chatEvents'

interface Props {
  events: ChatEvent[]
}

export function ProgressUtteranceList({ events }: Props) {
  const progressEvents = events.filter(
    (e): e is ProgressUtteranceEvent => e.type === 'progress_utterance',
  )

  if (progressEvents.length === 0) return null

  return (
    <ul className="flex flex-col gap-0.5 mt-1 px-1">
      {progressEvents.map((e, index) => (
        <li
          key={`${e.trigger_event}-${index}`}
          className="text-xs text-white/35 leading-snug font-mono truncate"
          title={e.text}
        >
          {e.text}
        </li>
      ))}
    </ul>
  )
}
