import { createContext, useContext, type ReactNode } from 'react'
import { de } from '@/lib/i18n/de'
import { en } from '@/lib/i18n/en'
import { useUiStore } from '@/state/uiStore'
import type { Locale, TextCatalog } from '@/lib/i18n/types'

const catalogs: Record<Locale, TextCatalog> = { en, de }

interface TranslationContextValue {
  locale: Locale
  t: (key: string, values?: Record<string, string | number>) => string
}

const TranslationContext = createContext<TranslationContextValue | null>(null)

function translate(locale: Locale, key: string, values?: Record<string, string | number>) {
  const template = catalogs[locale][key] ?? catalogs.en[key] ?? key
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(values?.[name] ?? `{${name}}`))
}

export function translateCurrent(key: string, values?: Record<string, string | number>) {
  return translate(useUiStore.getState().locale, key, values)
}

export function TranslationProvider({ children }: { children: ReactNode }) {
  const locale = useUiStore((state) => state.locale)
  return (
    <TranslationContext.Provider value={{ locale, t: (key, values) => translate(locale, key, values) }}>
      {children}
    </TranslationContext.Provider>
  )
}

export function useTranslation() {
  const context = useContext(TranslationContext)
  if (!context) throw new Error('useTranslation must be used within TranslationProvider.')
  return context
}
