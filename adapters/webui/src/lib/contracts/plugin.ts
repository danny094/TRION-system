export interface PluginSummary {
  id: string
  name: string
  version: string
  author: string
  description: string
  kind: 'app' | 'widget' | 'theme' | 'panel'
  mount: string
  icon: string
  entry: string
  enabled: boolean
  requiresMcp: string[]
  missingMcp: string[]
}
