import type { PluginSummary } from '@/lib/contracts/plugin'
import { PluginHostMount } from '@/features/plugins/components/PluginHostMount'
import { pluginAssetUrl, pluginEntryMode } from '@/lib/contracts/pluginHost'

export function PluginFrame({ plugin }: { plugin: PluginSummary | undefined }) {
  if (!plugin) {
    return <div className="flex h-full items-center justify-center text-sm text-white/35">Plugin nicht gefunden.</div>
  }
  if (pluginEntryMode(plugin) === 'host') {
    return <PluginHostMount plugin={plugin} />
  }
  if (!plugin.entry.toLowerCase().endsWith('.html')) {
    return <div className="flex h-full items-center justify-center px-8 text-center text-sm text-white/35">Unterstuetzt werden aktuell `index.html` fuer iframe-Plugins oder `entry.js` fuer Host-Plugins.</div>
  }
  return (
    <iframe
      src={pluginAssetUrl(plugin, plugin.entry)}
      title={plugin.name}
      className="h-full w-full border-0 bg-black"
      sandbox="allow-scripts allow-same-origin allow-forms allow-downloads"
    />
  )
}
