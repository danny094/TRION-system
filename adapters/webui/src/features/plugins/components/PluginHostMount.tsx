import type { PluginSummary } from '@/lib/contracts/plugin'
import { createPluginBridge, pluginAssetUrl } from '@/lib/contracts/pluginHost'
import { usePluginModule } from '@/features/plugins/hooks/usePluginModule'
import { useTranslation } from '@/lib/i18n'

export function PluginHostMount({ plugin }: { plugin: PluginSummary }) {
  const { Component, error } = usePluginModule(plugin)
  const { t } = useTranslation()
  if (error) {
    return <div className="flex h-full items-center justify-center px-8 text-center text-sm text-red-200/75">{error}</div>
  }
  if (!Component) {
    return <div className="flex h-full items-center justify-center text-sm text-white/35">{t('plugins.loadingModule')}</div>
  }
  return (
    <div className="h-full overflow-auto">
      <Component
        plugin={plugin}
        bridge={createPluginBridge(plugin)}
        assetUrl={(assetPath) => pluginAssetUrl(plugin, assetPath)}
      />
    </div>
  )
}
