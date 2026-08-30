import { useEffect } from 'react'
import { useWindowStore } from '@/state/windowStore'
import { WindowFrame } from './WindowFrame'
import { ChatPanelFrame } from './ChatPanelFrame'
import { AnimatePresence, motion } from 'framer-motion'
import { SettingsWindow } from '@/features/settings/components/SettingsWindow'
import { LaunchpadWindow } from '@/features/launchpad/components/LaunchpadWindow'
import { ApiKeysPanel } from '@/features/settings/components/ApiKeysPanel'
import { ModelleWindow } from '@/features/modelle/ModelleWindow'
import { McpsWindow } from '@/features/mcps/components/McpsWindow'
import { McpSettingsWindow } from '@/features/mcps/components/McpSettingsWindow'
import { PluginsWindow } from '@/features/plugins/components/PluginsWindow'
import { PluginWindow } from '@/features/plugins/components/PluginWindow'
import { MemoryWindow } from '@/features/memory/components/MemoryWindow'
import { AppIcon } from '@/components/icons/AppIcon'
import { getApp } from '@/lib/contracts/appRegistry'
import { useMcpsStore } from '@/features/mcps/state/mcpsStore'
import { findMcpHostApp, isMcpSettingsAppId, mcpNameFromSettingsAppId } from '@/lib/contracts/mcpHostApps'
import { findPluginApp, isPluginAppId, pluginIdFromAppId } from '@/lib/contracts/pluginApps'
import { usePluginStore } from '@/features/plugins/state/pluginStore'
import { useTranslation } from '@/lib/i18n'

export function WindowManager() {
  const { windows, updateWindow, focusWindow } = useWindowStore()
  const mcps = useMcpsStore((s) => s.items)
  const plugins = usePluginStore((s) => s.items)
  const refreshPlugins = usePluginStore((s) => s.refresh)
  const { t } = useTranslation()

  useEffect(() => {
    if (plugins.length === 0) {
      void refreshPlugins()
    }
  }, [plugins.length, refreshPlugins])

  const floatingWindows = windows.filter(w => w.appId !== 'chat' && !w.minimized)
  const minimizedWindows = windows.filter(w => w.appId !== 'chat' && w.minimized)
  const panelWindows = windows.filter(w => w.appId === 'chat')

  function restore(windowId: string) {
    updateWindow(windowId, { minimized: false })
    focusWindow(windowId)
  }

  return (
    <>
      {/* Floating windows */}
      <div className="absolute inset-0 pointer-events-none z-40 overflow-hidden">
        <AnimatePresence>
          {floatingWindows.map((win) => (
            <WindowFrame key={win.windowId} windowState={win}>
              {win.appId === 'settings' ? (
                <SettingsWindow />
              ) : win.appId === 'launchpad' ? (
                <LaunchpadWindow />
              ) : win.appId === 'api-settings' ? (
                <ApiKeysPanel />
              ) : win.appId === 'modelle' ? (
                <ModelleWindow />
              ) : win.appId === 'mcp' ? (
                <McpsWindow />
              ) : win.appId === 'plugins' ? (
                <PluginsWindow />
              ) : win.appId === 'memory' ? (
                <MemoryWindow />
              ) : isMcpSettingsAppId(win.appId) ? (
                <McpSettingsWindow mcpName={mcpNameFromSettingsAppId(win.appId)} />
              ) : isPluginAppId(win.appId) ? (
                <PluginWindow plugin={plugins.find((item) => item.id === pluginIdFromAppId(win.appId))} />
              ) : (
                <div className="flex items-center justify-center h-full text-white/30 text-sm">
                  {win.appId}
                </div>
              )}
            </WindowFrame>
          ))}
        </AnimatePresence>
      </div>

      {/* Minimized tray – above dock */}
      <AnimatePresence>
        {minimizedWindows.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="fixed bottom-[104px] left-1/2 -translate-x-1/2 flex items-center gap-2 z-50 pointer-events-auto"
          >
            {minimizedWindows.map((win) => {
              const app = getApp(win.appId) || findMcpHostApp(mcps, win.appId) || findPluginApp(plugins, win.appId)
              return (
                <button
                  key={win.windowId}
                  onClick={() => restore(win.windowId)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-full glass border border-white/10 hover:border-white/25 hover:bg-white/10 transition-all text-xs text-white/60 hover:text-white/90 select-none"
                  title={t('window.restore', { title: win.title })}
                >
                  {app && <AppIcon name={app.iconName} src={app.iconUrl} className="w-3.5 h-3.5" />}
                  <span>{win.title}</span>
                </button>
              )
            })}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Chat Panel */}
      <AnimatePresence>
        {panelWindows.filter(w => !w.minimized).map((win) => (
          <ChatPanelFrame key={win.windowId} windowState={win} />
        ))}
      </AnimatePresence>
    </>
  )
}
