import React, { useEffect, useState } from 'react'
import type { PluginHostComponent } from '@/lib/contracts/pluginHost'
import { pluginAssetUrl } from '@/lib/contracts/pluginHost'
import type { PluginSummary } from '@/lib/contracts/plugin'
import { useTranslation } from '@/lib/i18n'

interface PluginModuleState {
  Component: PluginHostComponent | null
  error: string | null
}

export function usePluginModule(plugin: PluginSummary | undefined): PluginModuleState {
  const [state, setState] = useState<PluginModuleState>({ Component: null, error: null })
  const { t } = useTranslation()

  useEffect(() => {
    if (!plugin) {
      setState({ Component: null, error: null })
      return
    }
    let cancelled = false
    ;(window as typeof window & { __TRION_REACT__?: typeof React }).__TRION_REACT__ = React
    import(/* @vite-ignore */ pluginAssetUrl(plugin, plugin.entry))
      .then((mod) => {
        if (cancelled) return
        const Component = normalizePluginComponent(mod.default)
        setState(Component ? { Component, error: null } : { Component: null, error: t('plugins.noDefaultExport') })
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setState({ Component: null, error: error instanceof Error ? error.message : t('plugins.loadFailed') })
      })
    return () => {
      cancelled = true
    }
  }, [plugin, t])

  return state
}

function normalizePluginComponent(value: unknown): PluginHostComponent | null {
  return typeof value === 'function' ? (value as PluginHostComponent) : null
}
