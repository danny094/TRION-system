import { useEffect, useState } from 'react'
import { errorMessage } from '@/features/settings/providerSettingsHelpers'
import {
  fetchAutonomyProfile,
  updateAutonomyProfile,
  type AutonomyProfile,
} from '@/features/settings/autonomyApi'

const DEFAULT_PROFILE: AutonomyProfile = {
  mode: 'halbautomatisch',
  planning_depth: 'normal',
  wait_behavior: '30sek',
  safety_level: 'standard',
  error_behavior: 'retry',
  loop_detection_enabled: true,
  loop_detection_sensitivity: 3,
}

type ProfileField = keyof AutonomyProfile

export function useAutonomyProfile() {
  const [profile, setProfile] = useState<AutonomyProfile>(DEFAULT_PROFILE)
  const [loading, setLoading] = useState(true)
  const [savingField, setSavingField] = useState<ProfileField | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)

  useEffect(() => {
    void load()
  }, [])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const payload = await fetchAutonomyProfile()
      setProfile(payload.profile)
    } catch (err) {
      setError(errorMessage(err, 'Autonomie-Einstellungen konnten nicht geladen werden.'))
    } finally {
      setLoading(false)
    }
  }

  async function updateField<K extends ProfileField>(
    field: K,
    value: AutonomyProfile[K]
  ) {
    const previous = profile
    const next = { ...previous, [field]: value }
    setProfile(next)
    setSavingField(field)
    setError(null)
    setStatus(null)
    try {
      const payload = await updateAutonomyProfile({ [field]: value })
      setProfile(payload.profile)
      setStatus('Gespeichert')
    } catch (err) {
      setProfile(previous)
      setError(errorMessage(err, 'Autonomie-Einstellung konnte nicht gespeichert werden.'))
    } finally {
      setSavingField(null)
    }
  }

  return {
    profile,
    loading,
    savingField,
    error,
    status,
    load,
    updateField,
  }
}
