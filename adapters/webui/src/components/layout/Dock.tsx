import { useDroppable } from '@dnd-kit/core'
import { SortableContext, horizontalListSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { X } from 'lucide-react'
import { useDockStore, type DockApp } from '@/state/dockStore'
import { useWindowStore } from '@/state/windowStore'
import { AppIcon } from '@/components/icons/AppIcon'
import { cn } from '@/lib/utils'
import { useTranslation } from '@/lib/i18n'

export const DOCK_DROP_ID = 'dock-drop-zone'

export function Dock() {
  const { apps, removeApp } = useDockStore()
  const { openWindow } = useWindowStore()
  const { t } = useTranslation()

  const { setNodeRef, isOver } = useDroppable({ id: DOCK_DROP_ID })

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'fixed bottom-6 left-1/2 -translate-x-1/2 glass px-6 py-4 rounded-[2rem] flex items-center justify-center gap-4 transition-all duration-300 min-w-[200px] min-h-[80px] z-50',
        isOver && 'ring-2 ring-primary/50 shadow-[0_0_30px_rgba(234,179,8,0.2)]'
      )}
    >
      <SortableContext items={apps.map((a) => a.id)} strategy={horizontalListSortingStrategy}>
        {apps.length === 0 ? (
          <p className={cn(
            'text-xs font-medium tracking-wide transition-colors select-none',
            isOver ? 'text-primary/70' : 'text-white/20'
          )}>
            {isOver ? t('dock.dropToAdd') : t('dock.dropHint')}
          </p>
        ) : (
          apps.map((app) => (
            <SortableDockItem
              key={app.id}
              app={app}
              onOpen={() => openWindow(app.openArgs)}
              onRemove={() => removeApp(app.id)}
              removeLabel={t('dock.remove')}
            />
          ))
        )}
      </SortableContext>

      {/* Drop target hint when dragging over empty dock */}
      {apps.length > 0 && isOver && (
        <div className="w-14 h-14 rounded-2xl border-2 border-dashed border-primary/40 flex items-center justify-center animate-pulse">
          <span className="text-primary/40 text-xl">+</span>
        </div>
      )}
    </div>
  )
}

interface SortableDockItemProps {
  app: DockApp
  onOpen: () => void
  onRemove: () => void
  removeLabel: string
}

function SortableDockItem({ app, onOpen, onRemove, removeLabel }: SortableDockItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: app.id,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn('relative group', isDragging && 'opacity-40')}
    >
      {/* App icon button */}
      <button
        {...listeners}
        {...attributes}
        onClick={onOpen}
        className={cn(
          'w-14 h-14 rounded-2xl overflow-hidden transition-all duration-200 shadow-lg cursor-pointer',
          'hover:scale-110 hover:shadow-[0_4px_20px_rgba(0,0,0,0.4)] active:scale-95'
        )}
        title={app.label}
      >
        <AppIcon name={app.iconName} src={app.iconUrl} className="w-full h-full" />
      </button>

      {/* Remove button – visible on hover */}
      <button
        onClick={(e) => { e.stopPropagation(); onRemove() }}
        className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-black/70 border border-white/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500/80"
        title={removeLabel}
      >
        <X className="w-2.5 h-2.5 text-white" />
      </button>

      {/* Label tooltip */}
      <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[9px] text-white/40 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity select-none pointer-events-none">
        {app.label}
      </span>
    </div>
  )
}
