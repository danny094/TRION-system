import type { PluginSummary } from '@/lib/contracts/plugin'
import { PluginFrame } from '@/features/plugins/components/PluginFrame'

export function PluginWindow({ plugin }: { plugin: PluginSummary | undefined }) {
  return <PluginFrame plugin={plugin} />
}
