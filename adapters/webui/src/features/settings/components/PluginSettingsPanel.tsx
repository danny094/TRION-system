import type { PluginSummary } from '@/lib/contracts/plugin'
import { PluginFrame } from '@/features/plugins/components/PluginFrame'

export function PluginSettingsPanel({ plugin }: { plugin: PluginSummary | undefined }) {
  return (
    <section className="h-full min-h-[520px] overflow-hidden rounded-[22px] border border-white/8 bg-black/30">
      <PluginFrame plugin={plugin} />
    </section>
  )
}
