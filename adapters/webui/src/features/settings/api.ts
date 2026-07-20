import { fetchApi } from '@/lib/api/client'

export type ProviderId = 'ollama' | 'ollama_cloud' | 'openai' | 'anthropic' | 'openrouter' | 'minimax'
export type ModelRole = 'THINKING' | 'CONTROL' | 'OUTPUT'

export interface ModelCatalogEntry {
  name: string
  provider: ProviderId
  source: string
  selected: boolean
  size?: number
  category?: string
}

export interface ModelCatalogResponse {
  models: ModelCatalogEntry[]
  effective: {
    OUTPUT_MODEL: string
    OUTPUT_PROVIDER: ProviderId
  }
  providers: ProviderId[]
}

export interface EffectiveSettingValue {
  value: string
  source: 'override' | 'env' | 'default'
}

export interface EffectiveModelSettingsResponse {
  effective: Record<string, EffectiveSettingValue>
  defaults: Record<string, string>
}

export interface ModelSettingsUpdatePayload {
  THINKING_MODEL?: string
  THINKING_PROVIDER?: ProviderId
  CONTROL_MODEL?: string
  CONTROL_PROVIDER?: ProviderId
  OUTPUT_MODEL?: string
  OUTPUT_PROVIDER?: ProviderId
}

export interface ModelSettingsUpdateResponse {
  success: boolean
  saved: Record<string, string>
}

export function fetchModelCatalog(): Promise<ModelCatalogResponse> {
  return fetchApi<ModelCatalogResponse>('/models/catalog')
}

export function fetchEffectiveModelSettings(): Promise<EffectiveModelSettingsResponse> {
  return fetchApi<EffectiveModelSettingsResponse>('/settings/models/effective')
}

export function updateModelSettings(
  payload: ModelSettingsUpdatePayload
): Promise<ModelSettingsUpdateResponse> {
  return fetchApi<ModelSettingsUpdateResponse>('/settings/models', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
