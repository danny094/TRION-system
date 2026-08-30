import { useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { useDraggable } from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'
import { useWindowStore } from '@/state/windowStore'
import { useDockStore } from '@/state/dockStore'
import { APP_REGISTRY, type AppDefinition } from '@/lib/contracts/appRegistry'
import { AppIcon } from '@/components/icons/AppIcon'
import { cn } from '@/lib/utils'
import { useMcpsStore } from '@/features/mcps/state/mcpsStore'
import { launchpadAppsFromMcps } from '@/lib/contracts/mcpHostApps'
import { usePluginStore } from '@/features/plugins/state/pluginStore'
import { launchpadAppsFromPlugins } from '@/lib/contracts/pluginApps'
import { useTranslation } from '@/lib/i18n'

export function LaunchpadWindow() {
  const items = useMcpsStore((s) => s.items)
  const refresh = useMcpsStore((s) => s.refresh)
  const plugins = usePluginStore((s) => s.items)
  const refreshPlugins = usePluginStore((s) => s.refresh)
  const { t } = useTranslation()
  const apps = useMemo(() => [...APP_REGISTRY, ...launchpadAppsFromMcps(items), ...launchpadAppsFromPlugins(plugins)], [items, plugins])

  useEffect(() => {
    if (items.length === 0) {
      void refresh()
    }
    if (plugins.length === 0) {
      void refreshPlugins()
    }
  }, [items.length, plugins.length, refresh, refreshPlugins])

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="grid grid-cols-4 gap-5 content-start">
        {apps.map((app, i) => (
          <DraggableAppIcon key={app.id} app={app} index={i} />
        ))}
      </div>
      <div className="mt-auto pt-4 border-t border-white/5 text-[10px] text-white/20 text-center select-none">
        {t('launchpad.dragHint')}
      </div>
    </div>
  )
}

interface DraggableAppIconProps {
  app: AppDefinition
  index: number
}

function DraggableAppIcon({ app, index }: DraggableAppIconProps) {
  const { openWindow } = useWindowStore()
  const isPinned = useDockStore((s) => s.hasApp(app.id))
  const { t } = useTranslation()

  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `launch-${app.id}`,
    data: { appId: app.id },
    disabled: !app.canPin,
  })

  const style = transform
    ? { transform: CSS.Translate.toString(transform) }
    : undefined

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.06, duration: 0.2 }}
      className="relative"
    >
      {/* Drag handle + visual icon — click handled here, drag activates after 8px movement */}
      <div
        ref={setNodeRef}
        style={style}
        {...listeners}
        {...attributes}
        onClick={() => openWindow(app.openArgs)}
        className={cn(
          'flex flex-col items-center gap-2.5 p-3 rounded-xl transition-all duration-150 group',
          app.canPin ? 'cursor-grab active:cursor-grabbing' : 'cursor-default',
          isDragging ? 'opacity-50 scale-95' : 'hover:bg-white/8'
        )}
      >
        <div className={cn(
          'relative w-14 h-14 rounded-2xl overflow-hidden transition-all duration-200 shadow-lg',
          isDragging
            ? 'shadow-[0_0_20px_rgba(234,179,8,0.3)] scale-95'
            : 'group-hover:scale-105'
        )}>
          <AppIcon name={app.iconName} src={app.iconUrl} className="w-full h-full" />

          {/* Pinned indicator dot */}
          {isPinned && (
            <span className="absolute bottom-1 right-1 w-1.5 h-1.5 rounded-full bg-primary/80" />
          )}
        </div>

        <span className="text-[11px] text-white/50 group-hover:text-white/80 transition-colors leading-tight text-center select-none">
          {app.label}
        </span>

        {!app.canPin && (
          <span className="text-[9px] text-white/25 uppercase tracking-wide select-none">
            {t('launchpad.quickLaunch')}
          </span>
        )}
      </div>

    </motion.div>
  )
}
