import { useEffect, useMemo } from 'react'
import { useMcpsStore } from '../state/mcpsStore'
import { AddMcpModal } from './AddMcpModal'
import { McpsSidebar } from './McpsSidebar'
import { AboutView } from './views/AboutView'
import { AllView } from './views/AllView'
import { InstallView } from './views/InstallView'
import { UninstallView } from './views/UninstallView'
import { FilesView } from './views/FilesView'
import { NewsView } from './views/NewsView'

const INSTALL_PATH = '~/.trion/mcp'

export function McpsWindow() {
  const installerView = useMcpsStore((s) => s.installerView)
  const items = useMcpsStore((s) => s.items)
  const modalOpen = useMcpsStore((s) => s.modalOpen)
  const saving = useMcpsStore((s) => s.saving)
  const error = useMcpsStore((s) => s.error)
  const setInstallerView = useMcpsStore((s) => s.setInstallerView)
  const openModal = useMcpsStore((s) => s.openModal)
  const closeModal = useMcpsStore((s) => s.closeModal)
  const refresh = useMcpsStore((s) => s.refresh)
  const uploadBundle = useMcpsStore((s) => s.uploadBundle)
  const toggleByName = useMcpsStore((s) => s.toggleByName)
  const removeByName = useMcpsStore((s) => s.removeByName)

  useEffect(() => {
    if (items.length === 0) {
      void refresh()
    }
  }, [items.length, refresh])

  const { activeCount, offlineCount } = useMemo(() => {
    const active = items.filter((m) => m.enabled && m.online).length
    return { activeCount: active, offlineCount: items.length - active }
  }, [items])

  return (
    <div className="flex h-full text-sm">
      <McpsSidebar
        view={installerView}
        onSelectView={setInstallerView}
        activeCount={activeCount}
      />

      <main className="flex flex-1 flex-col overflow-hidden">
        {error && (
          <div className="shrink-0 border-b border-rose-500/20 bg-rose-500/[0.06] px-8 py-2.5 text-xs text-rose-200">
            {error}
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-8 py-7">
          {installerView === 'about' && (
            <AboutView
              installedCount={items.length}
              activeCount={activeCount}
              offlineCount={offlineCount}
            />
          )}
          {installerView === 'all' && (
            <AllView
              items={items}
              saving={saving}
              onToggle={(name) => void toggleByName(name)}
            />
          )}
          {installerView === 'install' && (
            <InstallView
              installPath={INSTALL_PATH}
              onPickFile={(file) => void uploadBundle(file)}
              onOpenPicker={openModal}
            />
          )}
          {installerView === 'uninstall' && (
            <UninstallView
              items={items}
              saving={saving}
              onRemove={(name) => void removeByName(name)}
            />
          )}
          {installerView === 'files' && <FilesView />}
          {installerView === 'news' && <NewsView />}
        </div>
      </main>

      {modalOpen && <AddMcpModal onClose={closeModal} />}
    </div>
  )
}
