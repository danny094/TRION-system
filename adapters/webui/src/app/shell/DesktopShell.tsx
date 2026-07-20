import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { DndContext, DragOverlay, pointerWithin, PointerSensor, useSensor, useSensors, type DragEndEvent, type DragStartEvent } from '@dnd-kit/core'
import { arrayMove } from '@dnd-kit/sortable'
import { SearchBar } from '@/components/layout/SearchBar'
import { Dock, DOCK_DROP_ID } from '@/components/layout/Dock'
import { WindowManager } from '@/components/windows/WindowManager'
import { LaunchpadButton } from '@/components/layout/LaunchpadButton'
import { DesktopClock } from '@/components/layout/DesktopClock'
import { DesktopContextMenu } from '@/components/layout/DesktopContextMenu'
import { useDockStore } from '@/state/dockStore'
import { useUiStore, FONT_SIZE_PX } from '@/state/uiStore'
import { APP_REGISTRY } from '@/lib/contracts/appRegistry'
import { AppIcon } from '@/components/icons/AppIcon'
import { useMcpsStore } from '@/features/mcps/state/mcpsStore'
import { findMcpHostApp, launchpadAppsFromMcps } from '@/lib/contracts/mcpHostApps'

export function DesktopShell() {
  const { addApp, hasApp, reorderApps, apps: dockApps } = useDockStore()
  const { fontSize, backgroundImage, accentColor } = useUiStore()
  const mcps = useMcpsStore((s) => s.items)
  const [draggingAppId, setDraggingAppId] = useState<string | null>(null)
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null)

  function handleContextMenu(e: React.MouseEvent) {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY })
  }

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  )

  useEffect(() => {
    document.documentElement.style.fontSize = `${FONT_SIZE_PX[fontSize]}px`
  }, [fontSize])

  useEffect(() => {
    document.documentElement.style.setProperty('--color-primary', accentColor)
  }, [accentColor])

  function handleDragStart(event: DragStartEvent) {
    const appId = event.active.data.current?.appId as string | undefined
    if (appId) setDraggingAppId(appId)
  }

  function handleDragEnd(event: DragEndEvent) {
    setDraggingAppId(null)
    const { active, over } = event
    if (!over) return

    const isFromLaunchpad = String(active.id).startsWith('launch-')

    if (isFromLaunchpad) {
      // Drop from Launchpad → Dock: accept on drop-zone or on top of any existing dock item
      const appId = active.data.current?.appId as string | undefined
      const droppedOnDock = over.id === DOCK_DROP_ID || dockApps.some((a) => a.id === over.id)
      if (appId && droppedOnDock && !hasApp(appId)) {
        const def = APP_REGISTRY.find((a) => a.id === appId) || findMcpHostApp(mcps, appId)
        if (def?.canPin) {
          addApp({ id: def.id, label: def.label, iconName: def.iconName, iconUrl: def.iconUrl, color: def.color, openArgs: def.openArgs })
        }
      }
    } else {
      // Dock-internal sort: active and over are both dock app ids
      const activeId = String(active.id)
      const overId = String(over.id)
      if (activeId !== overId && over.id !== DOCK_DROP_ID) {
        const oldIndex = dockApps.findIndex((a) => a.id === activeId)
        const newIndex = dockApps.findIndex((a) => a.id === overId)
        if (oldIndex !== -1 && newIndex !== -1) {
          reorderApps(arrayMove(dockApps, oldIndex, newIndex))
        }
      }
    }
  }

  const draggingApp = draggingAppId
    ? [...APP_REGISTRY, ...launchpadAppsFromMcps(mcps)].find((a) => a.id === draggingAppId && a.canPin)
    : null

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={pointerWithin}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div
        className="relative w-screen h-screen overflow-hidden bg-background text-foreground flex flex-col selection:bg-primary/30"
        style={backgroundImage ? { backgroundImage: `url(${backgroundImage})`, backgroundSize: 'cover', backgroundPosition: 'center' } : undefined}
        onContextMenu={handleContextMenu}
      >
        {/* Ambient Glow Effects */}
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
          <motion.div
            animate={{
              scale: [1, 1.05, 1],
              opacity: [0.15, 0.2, 0.15]
            }}
            transition={{
              duration: 12,
              repeat: Infinity,
              ease: "easeInOut"
            }}
            className="absolute -top-[20%] -left-[10%] w-[70vw] h-[70vw] bg-primary rounded-full blur-[140px] mix-blend-screen"
          />
          <motion.div
            animate={{
              scale: [1, 1.1, 1],
              opacity: [0.08, 0.12, 0.08]
            }}
            transition={{
              duration: 15,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 2
            }}
            className="absolute top-[40%] -right-[20%] w-[80vw] h-[80vw] bg-primary rounded-full blur-[160px] mix-blend-screen"
          />
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0IiBoZWlnaHQ9IjQiPgo8cmVjdCB3aWR0aD0iNCIgaGVpZ2h0PSI0IiBmaWxsPSJub25lIiAvPgo8cmVjdCB3aWR0aD0iMSIgaGVpZ2h0PSIxIiBmaWxsPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMDQpIiAvPgo8L3N2Zz4=')] opacity-60" />
        </div>

        {/* Main Content Area */}
        <main className="relative z-10 flex-1 w-full h-full flex flex-col pointer-events-none">
          <SearchBar />
          <div className="flex-1 w-full h-full mt-32 px-12 pb-32 pointer-events-auto">
            {/* Dashboard/Monitoring widgets will go here */}
          </div>
        </main>

        <WindowManager />
        <LaunchpadButton />
        <DesktopClock />
        <Dock />

        {/* Context Menu */}
        {contextMenu && (
          <>
            <div
              className="fixed inset-0 z-[998]"
              onClick={() => setContextMenu(null)}
              onContextMenu={(e) => { e.preventDefault(); setContextMenu(null) }}
            />
            <DesktopContextMenu
              x={contextMenu.x}
              y={contextMenu.y}
              onClose={() => setContextMenu(null)}
            />
          </>
        )}

        {/* Drag Overlay – floating ghost icon while dragging */}
        <DragOverlay dropAnimation={null}>
          {draggingApp ? (
            <div className="w-14 h-14 rounded-2xl overflow-hidden shadow-[0_0_24px_rgba(234,179,8,0.35)] opacity-90 scale-110">
              <AppIcon name={draggingApp.iconName} src={draggingApp.iconUrl} className="w-full h-full" />
            </div>
          ) : null}
        </DragOverlay>
      </div>
    </DndContext>
  )
}
