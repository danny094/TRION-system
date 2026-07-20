import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import {
  fetchEffectiveModelSettings,
  fetchModelCatalog,
  updateModelSettings,
  type ModelCatalogEntry,
  type ModelRole,
  type ModelSettingsUpdatePayload,
  type ProviderId,
} from '@/features/settings/api'
import {
  buildRoleState,
  errorMessage,
  type RoleState,
} from '@/features/settings/providerSettingsHelpers'
import { ModelsOverview } from './views/models/ModelsOverview'
import { ProviderSelectView } from './views/models/ProviderSelectView'
import { ModelSelectView } from './views/models/ModelSelectView'
import { cn } from '@/lib/utils'

type DrillRole = ModelRole | 'EMBEDDING'

type View =
  | { screen: 'overview' }
  | { screen: 'provider-select'; role: DrillRole; label: string }
  | { screen: 'model-select';    role: DrillRole; providerId: string; providerLabel: string; backLabel: string }

export function ProviderSettingsPanel() {
  const [view, setView]       = useState<View>({ screen: 'overview' })
  const [providers, setProviders]   = useState<ProviderId[]>([])
  const [models, setModels]         = useState<ModelCatalogEntry[]>([])
  const [roles, setRoles]           = useState<Record<ModelRole, RoleState> | null>(null)
  const [simpleMode, setSimpleMode] = useState(false)
  const [embeddingEnabled, setEmbeddingEnabled] = useState(true)
  const [embeddingProvider, setEmbeddingProvider] = useState('openai')
  const [embeddingModel, setEmbeddingModel]       = useState('text-embedding-3-small')
  const [loading, setLoading]   = useState(true)
  const [saving, setSaving]     = useState(false)
  const [error, setError]       = useState<string | null>(null)

  useEffect(() => { void loadAll() }, [])

  async function loadAll() {
    setLoading(true)
    setError(null)
    try {
      const [catalog, effective] = await Promise.all([
        fetchModelCatalog(),
        fetchEffectiveModelSettings(),
      ])
      setProviders(catalog.providers)
      setModels(catalog.models)
      setRoles(buildRoleState(effective))
    } catch (err) {
      setError(errorMessage(err, 'Provider-Daten konnten nicht geladen werden.'))
    } finally {
      setLoading(false)
    }
  }

  async function saveRole(role: ModelRole, providerId: string, modelName: string) {
    setSaving(true)
    setError(null)
    try {
      const payload: ModelSettingsUpdatePayload = {}
      if (role === 'THINKING') {
        payload.THINKING_PROVIDER = providerId as ProviderId
        payload.THINKING_MODEL    = modelName
      } else if (role === 'CONTROL') {
        payload.CONTROL_PROVIDER = providerId as ProviderId
        payload.CONTROL_MODEL    = modelName
      } else {
        payload.OUTPUT_PROVIDER = providerId as ProviderId
        payload.OUTPUT_MODEL    = modelName
      }
      if (simpleMode) {
        payload.CONTROL_PROVIDER = providerId as ProviderId
        payload.CONTROL_MODEL    = modelName
        payload.THINKING_PROVIDER = providerId as ProviderId
        payload.THINKING_MODEL    = modelName
      }
      await updateModelSettings(payload)
      await loadAll()
    } catch (err) {
      setError(errorMessage(err, 'Modell konnte nicht gespeichert werden.'))
    } finally {
      setSaving(false)
    }
  }

  function handleModelSelect(model: string) {
    if (view.screen !== 'model-select') return
    const { role, providerId } = view
    if (role === 'EMBEDDING') {
      setEmbeddingProvider(providerId)
      setEmbeddingModel(model)
      setView({ screen: 'overview' })
      return
    }
    void saveRole(role as ModelRole, providerId, model)
    setView({ screen: 'overview' })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-[12px] text-white/35">
        <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
        Provider werden geladen
      </div>
    )
  }

  if (!roles) {
    return <Banner kind="error">{error ?? 'Keine Provider-Daten.'}</Banner>
  }

  return (
    <div className="flex flex-col gap-2">
      {error && <Banner kind="error">{error}</Banner>}

      {view.screen === 'overview' && (
        <ModelsOverview
          roles={roles}
          simpleMode={simpleMode}
          embeddingEnabled={embeddingEnabled}
          embeddingProvider={embeddingProvider}
          embeddingModel={embeddingModel}
          onToggleSimple={() => setSimpleMode((v) => !v)}
          onToggleEmbedding={() => setEmbeddingEnabled((v) => !v)}
          onDrill={(target) =>
            setView({ screen: 'provider-select', role: target.role, label: target.label })
          }
        />
      )}

      {view.screen === 'provider-select' && (
        <ProviderSelectView
          role={view.role}
          label={view.label}
          providers={providers}
          onBack={() => setView({ screen: 'overview' })}
          onSelect={(providerId) =>
            setView({
              screen: 'model-select',
              role: view.role,
              providerId,
              providerLabel: view.label,
              backLabel: view.label,
            })
          }
        />
      )}

      {view.screen === 'model-select' && (
        <ModelSelectView
          role={view.role}
          providerId={view.providerId}
          providerLabel={view.providerLabel}
          backLabel={view.backLabel}
          models={models}
          activeModel={
            view.role === 'EMBEDDING'
              ? embeddingModel
              : roles[view.role as ModelRole]?.model ?? ''
          }
          saving={saving}
          onSelect={handleModelSelect}
          onBack={() =>
            setView({ screen: 'provider-select', role: view.role, label: view.backLabel })
          }
        />
      )}
    </div>
  )
}

function Banner({ kind, children }: { kind: 'error' | 'success'; children: React.ReactNode }) {
  const cls = kind === 'error'
    ? 'border-rose-500/20 bg-rose-500/[0.06] text-rose-200'
    : 'border-emerald-500/20 bg-emerald-500/[0.06] text-emerald-200'
  return <div className={cn('rounded-2xl border px-4 py-2.5 text-[12px]', cls)}>{children}</div>
}
