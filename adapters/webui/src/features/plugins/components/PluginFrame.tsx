import type { PluginSummary } from '@/lib/contracts/plugin'
import { pluginAssetUrl, pluginEntryMode } from '@/lib/contracts/pluginHost'

export function PluginFrame({ plugin }: { plugin: PluginSummary | undefined }) {
  if (!plugin) {
    return <div className="flex h-full items-center justify-center text-sm text-white/35">Plugin nicht gefunden.</div>
  }
  if (pluginEntryMode(plugin) === 'blocked') {
    return <div className="flex h-full items-center justify-center px-8 text-center text-sm text-white/35">Plugin execution is limited to sandboxed HTML entries until a trust authority exists.</div>
  }
  return (
    <iframe
      src={pluginAssetUrl(plugin, plugin.entry)}
      title={plugin.name}
      className="h-full w-full border-0 bg-black"
      sandbox="allow-scripts allow-forms allow-downloads"
    />
  )
}
