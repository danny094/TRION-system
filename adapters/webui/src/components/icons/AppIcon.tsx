import { cn } from '@/lib/utils'

import iconSettings from '@/assets/icons/icon-settings.svg'
import iconChat from '@/assets/icons/icon-chat.svg'
import iconApiSettings from '@/assets/icons/icon-api-settings.svg'
import iconModelle from '@/assets/icons/icon-modelle.svg'
import iconErscheinungsbild from '@/assets/icons/icon-erscheinungsbild.svg'
import iconLaunchpad from '@/assets/icons/icon-launchpad.svg'
import iconPlugins from '@/assets/icons/icon-Plugins.svg'
import iconMcp from '@/assets/icons/icon-mcp.svg'
import iconMemory from '@/assets/icons/icon-memory-save.svg'

const ICON_MAP: Record<string, string> = {
  settings: iconSettings,
  chat: iconChat,
  'api-settings': iconApiSettings,
  modelle: iconModelle,
  erscheinungsbild: iconErscheinungsbild,
  launchpad: iconLaunchpad,
  plugins: iconPlugins,
  mcp: iconMcp,
  memory: iconMemory,
}

interface AppIconProps {
  name?: string
  src?: string | null
  size?: number
  className?: string
}

export function AppIcon({ name, src, size = 32, className }: AppIconProps) {
  const resolvedSrc = src || (name ? ICON_MAP[name] : undefined)
  if (!resolvedSrc) return null
  return (
    <img
      src={resolvedSrc}
      width={size}
      height={size}
      className={cn('object-cover pointer-events-none select-none', className)}
      alt={name || 'icon'}
      draggable={false}
    />
  )
}
