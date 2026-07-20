import { useEffect, useState } from 'react'
import { errorMessage } from '@/features/settings/providerSettingsHelpers'
import {
  fetchMemoryDefaults,
  updateMemoryDefaults,
  type MemoryDefaults,
  type MemoryDerived,
  type MemoryDefaultsUpdate,
} from '@/features/settings/memoryDefaultsApi'

const DEFAULT_VALUES: MemoryDefaults = {
  memory_mode: 'global_enabled',
  do_not_remember: false,
  max_memory_hits: 5,
}

const DEFAULT_DERIVED: MemoryDerived = {
  allow_global_memory_read: true,
  allow_long_term_write: true,
}

type Field = keyof MemoryDefaults

export function useMemoryDefaults() {
  const [defaults, setDefaults] = useState<MemoryDefaults>(DEFAULT_VALUES)
  const [derived, setDerived] = useState<MemoryDerived>(DEFAULT_DERIVED)
  const [loading, setLoading] = useState(true)
  const [savingField, setSavingField] = useState<Field | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)

  useEffect(() => {
    void load()
  }, [])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const payload = await fetchMemoryDefaults()
      setDefaults(payload.defaults)
      setDerived(payload.derived)
    } catch (err) {
      setError(errorMessage(err, 'Memory-Defaults konnten nicht geladen werden.'))
    } finally {
      setLoading(false)
    }
  }

  async function applyUpdate(update: MemoryDefaultsUpdate) {
    const fields = Object.keys(update) as Field[]
    if (fields.length === 0) return
    const previousDefaults = defaults
    const previousDerived = derived
    setDefaults((current) => ({ ...current, ...update }))
    setSavingField(fields[0])
    setError(null)
    setStatus(null)
    try {
      const payload = await updateMemoryDefaults(update)
      setDefaults(payload.defaults)
      setDerived(payload.derived)
      setStatus('Gespeichert')
    } catch (err) {
      setDefaults(previousDefaults)
      setDerived(previousDerived)
      setError(errorMessage(err, 'Memory-Default konnte nicht gespeichert werden.'))
    } finally {
      setSavingField(null)
    }
  }

  return { defaults, derived, loading, savingField, error, status, load, applyUpdate }
}
